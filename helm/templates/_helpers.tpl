{{- define "gbdi.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* Secret holding DB_URL: chart-managed with postgres.enabled, else the user's. */}}
{{- define "gbdi.dbSecret" -}}
{{- if .Values.postgres.enabled -}}
{{ .Release.Name }}-db
{{- else -}}
{{ required "database.existingSecret is required when postgres.enabled=false" .Values.database.existingSecret }}
{{- end -}}
{{- end }}

{{- define "gbdi.dbUrlEnv" -}}
- name: DB_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "gbdi.dbSecret" . }}
      key: DB_URL
{{- end }}

{{/* Restricted pod security profile: both images run as a numeric non-root user. */}}
{{- define "gbdi.containerSecurityContext" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: [ALL]
{{- end }}

{{- define "gbdi.podSecurityContext" -}}
runAsNonRoot: true
seccompProfile:
  type: RuntimeDefault
{{- end }}
