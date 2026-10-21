{{- define "gbdi.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* Secret holding DB_URL (and POSTGRES_PASSWORD for the in-chart postgres):
     the user's when set, else chart-managed with postgres.enabled. */}}
{{- define "gbdi.dbSecret" -}}
{{- if .Values.database.existingSecret -}}
{{ .Values.database.existingSecret }}
{{- else if .Values.postgres.enabled -}}
{{ .Release.Name }}-db
{{- else -}}
{{ fail "database.existingSecret is required when postgres.enabled=false" }}
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
