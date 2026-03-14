import api from './api';
import type { TrainingQuiz } from '@/types';

export interface TrainingProgress {
  total_quizzes: number;
  completed: number;
  correct: number;
  accuracy: number;
  weak_areas: { category: string; accuracy: number }[];
  streak: number;
}

interface QuizApiResponse {
  questions: TrainingQuiz[];
  total: number;
}

interface AnswerResult {
  is_correct: boolean;
  correct_answer: string;
  explanation: { psychology: string; strategy: string; script: string };
  user_accuracy: number;
  category_accuracy: number;
}

export const trainingService = {
  async getQuiz(category?: string, difficulty?: number): Promise<TrainingQuiz[]> {
    const res = await api.get<QuizApiResponse>('/training/quiz', {
      params: { category, difficulty, count: 3 },
    });
    return res.data.questions;
  },

  async submitAnswer(
    questionData: Record<string, unknown>,
    answer: string,
  ): Promise<AnswerResult> {
    const res = await api.post<AnswerResult>('/training/quiz/answer', {
      question_id: questionData.id || '',
      answer,
      question_data: questionData,
    });
    return res.data;
  },

  async getProgress(): Promise<TrainingProgress> {
    const res = await api.get<{
      total_questions: number;
      correct_count: number;
      accuracy: number;
      streak_days: number;
      weak_points: { category: string; accuracy: number; total_questions: number; wrong_count: number }[];
      recent_categories: string[];
    }>('/training/progress');
    const d = res.data;
    return {
      total_quizzes: 100,
      completed: d.total_questions,
      correct: d.correct_count,
      accuracy: d.accuracy,
      weak_areas: d.weak_points.map((w) => ({ category: w.category, accuracy: w.accuracy })),
      streak: d.streak_days,
    };
  },

  async getWeakPoints(): Promise<{ category: string; accuracy: number; total_questions: number; wrong_count: number }[]> {
    const res = await api.get('/training/weak-points');
    return res.data;
  },
};
