/**
 * Module-level emitter — Provider 외부(예: axios interceptor)에서 토스트를 띄울 때 사용.
 * Provider 마운트 시 setEmitter() 로 실제 함수 주입.
 */
import type { ToastInput } from "./types";

type Emitter = (t: ToastInput) => number;

let _emit: Emitter = () => -1;

export function setEmitter(fn: Emitter) {
  _emit = fn;
}

export const toastBus = {
  show: (input: ToastInput) => _emit(input),
  info: (message: string, durationMs?: number) =>
    _emit({ message, variant: "info", durationMs }),
  success: (message: string, durationMs?: number) =>
    _emit({ message, variant: "success", durationMs }),
  warning: (message: string, durationMs?: number) =>
    _emit({ message, variant: "warning", durationMs }),
  error: (message: string, durationMs?: number) =>
    _emit({ message, variant: "error", durationMs }),
};
