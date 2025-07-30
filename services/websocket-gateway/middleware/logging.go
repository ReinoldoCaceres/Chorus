package middleware

import (
	"log"
	"net/http"
	"time"
)

type responseWriter struct {
	http.ResponseWriter
	status int
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.status = code
	rw.ResponseWriter.WriteHeader(code)
}

func Logging(logger *log.Logger, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		
		wrapped := &responseWriter{
			ResponseWriter: w,
			status:         http.StatusOK,
		}
		
		next.ServeHTTP(wrapped, r)
		
		logger.Printf(
			"%s %s %s %d %s",
			r.RemoteAddr,
			r.Method,
			r.URL.Path,
			wrapped.status,
			time.Since(start),
		)
	})
}