export type ToastVariant = "info" | "success" | "warning" | "error";

export type ToastInput = {
  message: string;
  variant?: ToastVariant;
  durationMs?: number;       // null/0 = sticky
  description?: string;
};

export type ToastItem = ToastInput & {
  id: number;
  createdAt: number;
};
