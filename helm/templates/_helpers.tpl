
{{- define "kadr.stdlabels" }}
"app.kubernetes.io/name": {{ .root.Release.Name }}
"app.kubernetes.io/managed-by": kuberentes-acme-dns-registrar
"app.kubernetes.io/instance": {{ .root.Release.Name }}
"app.kubernetes.io/version": {{ .root.Values.deployment.tag }}
"app.kubernetes.io/part-of": {{ .root.Release.Name }}
"app.kubernetes.io/component": kuberentes-acme-dns-registrar
"helm.sh/chart": {{ .root.Chart.Name }}-{{ .root.Chart.Version }}
{{- end }}