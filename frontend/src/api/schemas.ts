import { z } from 'zod'

// Every API response is parsed here, so a backend change shows up as a clear error,
// not as undefined values in the UI.

export const tokens = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.literal('bearer'),
})

export const documentSchema = z.object({
  id: z.string(),
  filename: z.string(),
  mime: z.string(),
  sha256: z.string(),
  status: z.string(),
  pages: z.number().nullable(),
  created_at: z.string(),
  duplicate: z.boolean(),
  job_id: z.string().nullable(),
})
export type DocumentOut = z.infer<typeof documentSchema>

export const batchResult = z.object({
  filename: z.string().nullable(),
  document: documentSchema.nullable(),
  error: z.string().nullable(),
  code: z.string().nullable(),
})
export type BatchResult = z.infer<typeof batchResult>

export const jobSchema = z.object({
  id: z.string(),
  document_id: z.string(),
  state: z.string(),
  attempts: z.number(),
  error_code: z.string().nullable(),
  error_detail: z.string().nullable(),
  dead_lettered: z.boolean(),
})
export type JobOut = z.infer<typeof jobSchema>

export const evidenceSchema = z.object({
  page: z.number(),
  text: z.string(),
  bbox: z.array(z.number()).length(4).nullable(),
  coordinate_system: z.string().nullable(),
  confidence: z.number().nullable(),
})

export const fieldSchema = z.object({
  id: z.string(),
  name: z.string(),
  value_raw: z.string().nullable(),
  value_normalized: z.string().nullable(),
  final_value: z.string().nullable(),
  source: z.string(),
  evidence_status: z.string(),
  evidence_independent: z.boolean(),
  risk_score: z.number().nullable(),
  calibrated_prob: z.number().nullable(),
  decision: z.string(),
  evidence: z.array(evidenceSchema),
  validations: z.array(z.object({ rule_id: z.string(), passed: z.boolean(), message: z.string() })),
})
export type FieldOut = z.infer<typeof fieldSchema>

export const pageSchema = z.object({
  number: z.number(),
  width: z.number(),
  height: z.number(),
  coordinate_system: z.string(),
  source: z.string(),
})
export type PageOut = z.infer<typeof pageSchema>

export const documentFields = z.object({
  document_id: z.string(),
  filename: z.string(),
  status: z.string(),
  run_version: z.string(),
  provider: z.string().nullable(),
  degraded_reason: z.string().nullable(),
  pages: z.array(pageSchema),
  fields: z.array(fieldSchema),
})
export type DocumentFields = z.infer<typeof documentFields>

export const queueItem = z.object({
  field_id: z.string(),
  document_id: z.string(),
  filename: z.string(),
  name: z.string(),
  value_raw: z.string().nullable(),
  risk_score: z.number().nullable(),
  created_at: z.string(),
})
export type QueueItem = z.infer<typeof queueItem>

export const auditEvent = z.object({
  id: z.string(),
  created_at: z.string(),
  actor_email: z.string().nullable(),
  action: z.string(),
  entity: z.string(),
  field_name: z.string().nullable(),
  old_value: z.string().nullable(),
  new_value: z.string().nullable(),
})
export type AuditEvent = z.infer<typeof auditEvent>

const block = z.object({ available: z.boolean(), source: z.string(), data: z.unknown().optional() })
export const report = z.object({
  test_comparison: block,
  s5_test: block,
  validation_comparison: block,
  prompt_round: block,
  s1_test: block,
  s5_s1_validation: block,
  s5_s4h_validation: block,
  note: z.string(),
})
export type Report = z.infer<typeof report>

const interval = z.array(z.number()).length(2).nullable()
export const comparisonSystem = z.object({
  system: z.string(),
  source: z.string(),
  model: z.string().nullable(),
  prompt: z.string().nullable(),
  n_documents: z.number(),
  fields: z.record(
    z.string(),
    z.object({ f1: z.number().nullable(), f1_ci95: interval, precision: z.number().nullable(),
               recall: z.number().nullable(), false_fill_rate: z.number().nullable() }),
  ),
  line_items_row_level: z.object({ f1: z.number().nullable(), f1_ci95: interval }),
  failures: z.object({ failed_extractions: z.number(), pass_fallbacks: z.number() }),
})
export const comparison = z.object({
  metrics_version: z.string(),
  split: z.string(),
  note: z.string(),
  systems: z.array(comparisonSystem),
})
export type Comparison = z.infer<typeof comparison>

export const problem = z.object({
  status: z.number(),
  title: z.string(),
  detail: z.string().optional(),
  code: z.string().optional(),
})
