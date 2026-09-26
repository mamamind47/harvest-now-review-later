// pqscan: per-host post-quantum TLS key-exchange probe.
//
// For each hostname it runs three independent probes:
//   pq_only  - ClientHello offers ONLY X25519MLKEM768. Success = server supports hybrid PQ.
//   default  - ClientHello offers X25519MLKEM768 first, then classical groups (like Chrome).
//              Records what the server actually negotiates.
//   http     - one HEAD / over the default connection, to read CDN fingerprint headers.
//
// Input: CSV with header "sector,host". Output: JSON lines on stdout.
package main

import (
	"bufio"
	"context"
	"crypto/tls"
	"crypto/x509"
	"encoding/csv"
	"encoding/json"
	"flag"
	"fmt"
	"net"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"
)

type Result struct {
	Sector       string            `json:"sector"`
	Host         string            `json:"host"`
	IPs          []string          `json:"ips,omitempty"`
	DNSErr       string            `json:"dns_err,omitempty"`
	PQOnlyOK     bool              `json:"pq_only_ok"`
	PQOnlyErr    string            `json:"pq_only_err,omitempty"`
	DefaultOK    bool              `json:"default_ok"`
	DefaultErr   string            `json:"default_err,omitempty"`
	DefaultCurve string            `json:"default_curve,omitempty"`
	TLSVersion   string            `json:"tls_version,omitempty"`
	CertSigAlg   string            `json:"cert_sig_alg,omitempty"`
	CertKeyAlg   string            `json:"cert_key_alg,omitempty"`
	CertIssuer   string            `json:"cert_issuer,omitempty"`
	CertNotAfter string            `json:"cert_not_after,omitempty"`
	HTTPStatus   int               `json:"http_status,omitempty"`
	HTTPErr      string            `json:"http_err,omitempty"`
	Headers      map[string]string `json:"headers,omitempty"`
	CDN          string            `json:"cdn,omitempty"`
	ScannedAt    string            `json:"scanned_at"`
}

var fingerprintHeaders = []string{
	"server", "via", "x-cache", "cf-ray", "cf-cache-status", "x-amz-cf-id", "x-amz-cf-pop",
	"x-akamai-transformed", "akamai-grn", "x-served-by", "x-fastly-request-id", "x-azure-ref",
	"x-msedge-ref", "x-cdn", "x-iinfo", "x-sucuri-id", "x-bdcdn-cache", "x-edge-location",
	"x-powered-by", "x-goog-hash", "alt-svc",
}

func curveName(id tls.CurveID) string {
	switch id {
	case tls.X25519MLKEM768:
		return "X25519MLKEM768"
	case tls.X25519:
		return "X25519"
	case tls.CurveP256:
		return "P-256"
	case tls.CurveP384:
		return "P-384"
	case tls.CurveP521:
		return "P-521"
	case 0:
		return "none(RSA-kx or TLS<=1.1)"
	}
	return fmt.Sprintf("0x%04x", uint16(id))
}

func handshake(host string, curves []tls.CurveID, timeout time.Duration) (*tls.Conn, error) {
	d := &net.Dialer{Timeout: timeout}
	cfg := &tls.Config{
		ServerName:       host,
		CurvePreferences: curves,
		// We measure key exchange, not PKI validity: an invalid chain must not hide the kx result.
		InsecureSkipVerify: true,
		NextProtos:         []string{"http/1.1"},
	}
	return tls.DialWithDialer(d, "tcp", net.JoinHostPort(host, "443"), cfg)
}

func guessCDN(h map[string]string) string {
	get := func(k string) string { return strings.ToLower(h[k]) }
	switch {
	case h["cf-ray"] != "" || strings.Contains(get("server"), "cloudflare"):
		return "cloudflare"
	case h["x-amz-cf-id"] != "" || strings.Contains(get("via"), "cloudfront"):
		return "cloudfront"
	case h["x-fastly-request-id"] != "" || strings.Contains(get("x-served-by"), "cache-"):
		return "fastly"
	case h["akamai-grn"] != "" || h["x-akamai-transformed"] != "" || strings.Contains(get("server"), "akamai"):
		return "akamai"
	case h["x-azure-ref"] != "" || h["x-msedge-ref"] != "":
		return "azure-frontdoor"
	case h["x-iinfo"] != "" || strings.Contains(get("x-cdn"), "imperva") || strings.Contains(get("x-cdn"), "incapsula"):
		return "imperva"
	case strings.Contains(get("server"), "gws") || strings.Contains(get("server"), "google"):
		return "google"
	case h["x-sucuri-id"] != "":
		return "sucuri"
	case strings.Contains(get("server"), "bigip") || strings.Contains(get("server"), "f5"):
		return "f5-bigip"
	}
	return ""
}

func scan(sector, host string, timeout time.Duration) Result {
	r := Result{Sector: sector, Host: host, ScannedAt: time.Now().UTC().Format(time.RFC3339)}

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	ips, err := net.DefaultResolver.LookupHost(ctx, host)
	cancel()
	if err != nil {
		r.DNSErr = err.Error()
		return r
	}
	r.IPs = ips

	if c, err := handshake(host, []tls.CurveID{tls.X25519MLKEM768}, timeout); err != nil {
		r.PQOnlyErr = err.Error()
	} else {
		r.PQOnlyOK = true
		c.Close()
	}

	c, err := handshake(host, []tls.CurveID{tls.X25519MLKEM768, tls.X25519, tls.CurveP256, tls.CurveP384}, timeout)
	if err != nil {
		r.DefaultErr = err.Error()
		return r
	}
	defer c.Close()
	st := c.ConnectionState()
	r.DefaultOK = true
	r.DefaultCurve = curveName(st.CurveID)
	r.TLSVersion = tls.VersionName(st.Version)
	if len(st.PeerCertificates) > 0 {
		leaf := st.PeerCertificates[0]
		r.CertSigAlg = leaf.SignatureAlgorithm.String()
		r.CertKeyAlg = leaf.PublicKeyAlgorithm.String()
		if leaf.PublicKeyAlgorithm == x509.RSA {
			r.CertKeyAlg = "RSA"
		}
		r.CertIssuer = leaf.Issuer.CommonName
		r.CertNotAfter = leaf.NotAfter.Format("2006-01-02")
	}

	// HEAD over the already-established connection.
	c.SetDeadline(time.Now().Add(timeout))
	req, _ := http.NewRequest("HEAD", "https://"+host+"/", nil)
	req.Header.Set("User-Agent", "Mozilla/5.0 (academic TLS key-exchange survey)")
	req.Close = true
	if err := req.Write(c); err != nil {
		r.HTTPErr = err.Error()
		return r
	}
	resp, err := http.ReadResponse(bufio.NewReader(c), req)
	if err != nil {
		r.HTTPErr = err.Error()
		return r
	}
	resp.Body.Close()
	r.HTTPStatus = resp.StatusCode
	r.Headers = map[string]string{}
	for _, k := range fingerprintHeaders {
		if v := resp.Header.Get(k); v != "" {
			r.Headers[k] = v
		}
	}
	r.CDN = guessCDN(r.Headers)
	return r
}

func main() {
	in := flag.String("in", "hosts.csv", "CSV with header sector,host")
	workers := flag.Int("workers", 8, "parallel hosts")
	timeout := flag.Duration("timeout", 10*time.Second, "per-step timeout")
	flag.Parse()

	f, err := os.Open(*in)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	rows, err := csv.NewReader(f).ReadAll()
	f.Close()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	jobs := make(chan []string)
	out := make(chan Result)
	var wg sync.WaitGroup
	for i := 0; i < *workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for row := range jobs {
				out <- scan(strings.TrimSpace(row[0]), strings.TrimSpace(row[1]), *timeout)
			}
		}()
	}
	go func() {
		for i, row := range rows {
			if i == 0 || len(row) < 2 || strings.HasPrefix(row[0], "#") {
				continue
			}
			jobs <- row
		}
		close(jobs)
		wg.Wait()
		close(out)
	}()
	enc := json.NewEncoder(os.Stdout)
	for r := range out {
		enc.Encode(r)
	}
}
