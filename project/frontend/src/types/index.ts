// ── User & Enterprise ──

export interface User {
  id: string;
  username: string;
  name: string;
  role: 'super_admin' | 'admin' | 'manager' | 'agent' | 'staff';
  avatar?: string;
  enterprise_id: string;
  created_at: string;
}

export interface Enterprise {
  id: string;
  name: string;
  industry: string;
  description?: string;
  config?: Record<string, unknown>;
  created_at: string;
}

// ── Script (三层话术) ──

export interface ScriptPsychology {
  customer_type: string;
  emotion_state: string;
  resistance_level: number;
  decision_stage: string;
  core_need: string;
}

export interface ScriptStrategy {
  approach: string;
  techniques: string[];
  timing: string;
  risk_level: 'low' | 'medium' | 'high';
  fallback?: string;
}

export interface ScriptContent {
  opening: string;
  body: string;
  closing: string;
  variations?: string[];
}

export interface Script {
  id: string;
  title: string;
  category: string;
  tags: string[];
  psychology: ScriptPsychology;
  strategy: ScriptStrategy;
  content: ScriptContent;
  usage_count: number;
  success_rate: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ScriptUsage {
  id: string;
  script_id: string;
  user_id: string;
  context: string;
  outcome: 'success' | 'partial' | 'failure';
  feedback?: string;
  used_at: string;
}

// ── Enterprise Memory ──

export interface PainPoint {
  id: string;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  frequency: number;
  related_products: string[];
  source: string;
  created_at: string;
}

export interface Product {
  id: string;
  name: string;
  description: string;
  features: string[];
  price_range?: string;
  target_audience: string;
  pain_points_solved: string[];
  created_at: string;
}

export interface Service {
  id: string;
  name: string;
  description: string;
  service_type: string;
  sla?: string;
  related_products: string[];
  created_at: string;
}

// ── Conversation ──

export interface Conversation {
  id: string;
  title: string;
  user_id: string;
  message_count: number;
  last_message?: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  cards?: Card[];
  suggested_actions?: SuggestedAction[];
  created_at: string;
}

export interface AIResponse {
  message: string;
  cards?: Card[];
  suggested_actions?: SuggestedAction[];
}

export interface Card {
  type: 'script' | 'diagnosis' | 'training' | 'data' | 'memory' | 'optimize-strategy' | 'annotation-card' | 'ab-test-card' | 'diagnosis-radar' | 'channel-material-card';
  title: string;
  data: Record<string, unknown>;
}

export interface SuggestedAction {
  label: string;
  command: string;
  description?: string;
}

// ── Training ──

export interface TrainingQuiz {
  id: string;
  question: string;
  options: { key: string; text: string }[];
  correct_answer: string;
  explanation: string;
  category: string;
  difficulty: 'easy' | 'medium' | 'hard';
}

export interface TrainingRecord {
  id: string;
  user_id: string;
  quiz_id: string;
  answer: string;
  is_correct: boolean;
  time_spent: number;
  created_at: string;
}

// ── Simulation ──

export interface SimulationSession {
  id: string;
  user_id: string;
  scenario: string;
  difficulty: 'easy' | 'medium' | 'hard';
  status: 'active' | 'completed' | 'abandoned';
  score?: number;
  feedback?: string;
  messages: SimulationMessage[];
  created_at: string;
}

export interface SimulationMessage {
  id: string;
  role: 'customer' | 'agent' | 'coach';
  content: string;
  hint?: string;
  score?: number;
  created_at: string;
}

// ── Diagnosis ──

export interface DiagnosisReport {
  id: string;
  user_id: string;
  conversation_text: string;
  overall_score: number;
  dimensions: {
    name: string;
    score: number;
    feedback: string;
    suggestions: string[];
  }[];
  highlights: string[];
  improvements: string[];
  recommended_scripts: Script[];
  created_at: string;
}

// ── Dashboard ──

export interface DashboardOverview {
  total_scripts: number;
  today_usage: number;
  avg_conversion_rate: number;
  training_completion_rate: number;
  scripts_trend: number;
  usage_trend: number;
  conversion_trend: number;
  training_trend: number;
}

export interface ScriptRanking {
  script_id: string;
  title: string;
  usage_count: number;
  success_rate: number;
  category: string;
}

export interface TeamStats {
  user_id: string;
  name: string;
  avatar?: string;
  scripts_used: number;
  training_score: number;
  conversion_rate: number;
  rank: number;
}

// ── Common ──

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiError {
  code: number;
  message: string;
  details?: string[];
}

// ── Optimization Loop (v1.1) ──

export interface OptimizationTask {
  id: string;
  status: 'pending' | 'diagnosing' | 'strategizing' | 'testing' | 'completed';
  classification: {
    traffic_quality: 'valid' | 'invalid' | 'gray';
    dialog_depth: 'ultra_short' | 'short' | 'normal';
    service_mode: 'robot' | 'human' | 'hybrid';
  };
  score_result: {
    overall: number;
    grade: string;
    dimensions: Record<string, { score: number; weight: number; details: string[] }>;
  };
  root_causes: { type: string; description: string; affected_turns: number[] }[];
  strategies: OptimizationStrategy[];
  created_at: string;
}

export interface OptimizationStrategy {
  id: string;
  priority: 'P0' | 'P1' | 'P2';
  problem: string;
  root_cause_type: 'config' | 'script' | 'traffic' | 'product';
  solution: string;
  current_script: string;
  suggested_script: string;
  expected_impact: string;
  risk_level: 'low' | 'medium' | 'high';
  status: 'pending' | 'adopted' | 'rejected' | 'modified';
}

export interface Annotation {
  id: string;
  turn_index: number;
  label: 'good' | 'bad' | 'neutral';
  strategy_type?: string;
  note?: string;
  is_ai_generated: boolean;
  confidence?: number;
  extractable?: boolean;
}

export interface ABTest {
  id: string;
  name: string;
  status: 'draft' | 'running' | 'paused' | 'completed';
  variants: ABTestVariant[];
  significance?: Record<string, { p_value: number; is_significant: boolean }>;
  recommendation?: string;
  created_at: string;
}

export interface ABTestVariant {
  id: string;
  name: string;
  is_control: boolean;
  traffic_ratio: number;
  metrics: {
    dialog_count: number;
    contact_rate: number;
    reply_rate: number;
    avg_depth: number;
    avg_score: number;
  };
}
