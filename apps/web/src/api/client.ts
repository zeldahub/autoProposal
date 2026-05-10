import axios, { AxiosError } from "axios";
import { toastBus } from "../ui/toast/bus";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "/api",
});

// 시작 시 저장된 토큰을 즉시 헤더에 부착
const saved = typeof localStorage !== "undefined" ? localStorage.getItem("lon.token") : null;
if (saved) {
  api.defaults.headers.common["Authorization"] = `Bearer ${saved}`;
}

// 글로벌 응답 인터셉터: 401 → 로그아웃, 5xx/네트워크 → 자동 토스트
api.interceptors.response.use(
  (r) => r,
  (err: AxiosError<any>) => {
    const status = err.response?.status;
    const config = err.config as any;
    const silent = config?.silent === true;
    const errBody = err.response?.data?.error;

    if (status === 401) {
      const url = String(config?.url || "");
      // 로그인/회원가입 자체는 401 응답이 자연스러우므로 (잘못된 비번 등)
      // 글로벌 로그아웃/리다이렉트 처리에서 제외한다.
      const isAuthEndpoint = url.includes("/auth/login") || url.includes("/auth/register");
      if (isAuthEndpoint) {
        return Promise.reject(err);
      }

      // 이미 로그인 페이지면 토큰 정리만 하고 리다이렉트 생략
      const onLoginPage = location.pathname.startsWith("/login");
      // 토큰 없이 호출한 경우 (헤더 미부착) — race condition 일 가능성 → 조용히 reject
      const hadToken = !!localStorage.getItem("lon.token");

      localStorage.removeItem("lon.token");
      localStorage.removeItem("lon.user");
      delete api.defaults.headers.common["Authorization"];

      if (!onLoginPage) {
        // /auth/me 등 자동 헬스체크는 토스트 생략
        const isAuthCheck = url.includes("/auth/me");
        if (hadToken && !isAuthCheck && !silent) {
          toastBus.warning("세션이 만료되었습니다. 다시 로그인하세요.");
        }
        location.assign(`/login?redirect=${encodeURIComponent(location.pathname)}`);
      }
    } else if (status === 403 && !silent) {
      toastBus.error(errBody?.message || "권한이 없습니다.");
    } else if (status && status >= 500 && !silent) {
      toastBus.error(errBody?.message || `서버 오류 (${status})`);
    } else if (!status && !silent) {
      toastBus.error("네트워크 오류 — 서버 연결을 확인하세요.");
    }
    return Promise.reject(err);
  }
);

// 도메인 헬퍼
export type LlmTestRequest = { provider: string; model: string; apiKey: string; projectUuid?: string };

export const llmTest = (p: LlmTestRequest) =>
  api.post("/llm/test", p).then((r) => r.data);

export const listCategories = () =>
  api.get("/categories").then((r) => r.data.data.items as { code: string; name: string }[]);

export type ProjectIn = {
  companyName?: string;
  projectName: string;
  goal?: string;
  scope?: string;
  schedule?: string;
  organization?: string;
  staff?: string;
  costDev?: string;
  costOps?: string;
  licenseInfo?: string;
  availability?: string;
  budget?: string;
  aiProvider?: string;
  aiModel?: string;
};

export const createProject = (p: ProjectIn) =>
  api.post("/projects", p).then((r) => r.data.data as { id: number; uuid: string });

export const listProjects = (page = 0, size = 20, q?: string) =>
  api.get("/projects", { params: { page, size, q } }).then((r) => r.data.data);

export const analyzeFiles = (form: FormData) =>
  api.post("/files/analyze", form, { headers: { "Content-Type": "multipart/form-data" } })
    .then((r) => r.data.data);

export type LlmCreds = { provider?: string; model?: string; apiKey?: string };

export const generatePptx = (projectUuid: string, categories: string[], llm?: LlmCreds) =>
  api.post(
    "/generate/pptx",
    { projectUuid, categories, ...llm },
    { responseType: "blob" }
  );

export const generateWbs = (projectUuid: string, phases = 5) =>
  api.post("/generate/wbs", { projectUuid, phases }, { responseType: "blob" });

// ── projects detail / artifacts / logs ──────────────────────────
export type ProjectDetail = {
  id: number; uuid: string; companyName?: string; projectName: string;
  goal?: string; scope?: string; schedule?: string; organization?: string;
  staff?: string; costDev?: string; costOps?: string; licenseInfo?: string;
  availability?: string; budget?: string;
  aiProvider?: string; aiModel?: string; status: string;
  createdAt?: string; updatedAt?: string;
};

export type ArtifactItem = {
  id: number; type: "PPTX" | "XLSX"; version: number;
  filename: string; sizeBytes: number; createdAt?: string;
  projectUuid?: string; projectName?: string;
};

export type LlmLogItem = {
  id: number; provider: string; model: string; purpose: string;
  inputTokens: number | null; outputTokens: number | null;
  latencyMs: number | null; httpStatus: number | null; errorCode: string | null;
  createdAt?: string;
};

export const getProject = (uuid: string) =>
  api.get(`/projects/${uuid}`).then((r) => r.data.data as ProjectDetail);

export const updateProject = (uuid: string, body: ProjectIn) =>
  api.put(`/projects/${uuid}`, body).then((r) => r.data.data as ProjectDetail);

export const deleteProject = (uuid: string) =>
  api.delete(`/projects/${uuid}`).then((r) => r.data);

export const cloneProject = (uuid: string, body: { newName?: string; includeAttachments?: boolean }) =>
  api.post(`/projects/${uuid}/clone`, body).then((r) => r.data.data as {
    uuid: string; id: number; sourceUuid: string; attachmentCount: number;
  });

// ── 휴지통 ───────────────────────────────────────────────
export type TrashItem = ProjectDetail & {
  deletedAt: string | null;
  artifactCount: number;
};

export const listTrashProjects = (params?: { page?: number; size?: number; q?: string }) =>
  api.get("/projects/trash", { params }).then((r) => r.data.data as {
    items: TrashItem[]; page: number; size: number; total: number;
  });

export const restoreProject = (uuid: string) =>
  api.post(`/projects/${uuid}/restore`).then((r) => r.data.data as { uuid: string; restored: boolean });

export const purgeProject = (uuid: string) =>
  api.delete(`/projects/${uuid}/purge`).then((r) => r.data.data as {
    uuid: string; purged: boolean; artifactCount: number; attachmentCount: number;
  });

export const listProjectArtifacts = (uuid: string) =>
  api.get(`/projects/${uuid}/artifacts`).then((r) => r.data.data.items as ArtifactItem[]);

export const listProjectLlmLogs = (uuid: string) =>
  api.get(`/projects/${uuid}/llm-logs`).then((r) => r.data.data.items as LlmLogItem[]);

// ── attachments + analysis + preview ─────────────────────
export type AttachmentItem = {
  id: number; slot: "NOTICE" | "REFERENCE";
  filename: string; mimeType: string; sizeBytes: number;
  mongoDocId: string | null; createdAt: string | null;
};

export const listProjectAttachments = (uuid: string) =>
  api.get(`/projects/${uuid}/attachments`).then((r) => r.data.data.items as AttachmentItem[]);

export type ProjectAnalysis = {
  fields: Record<string, string>;
  confidence: Record<string, number>;
  summary: string;
  model?: string;
  createdAt?: string;
};

export const getProjectAnalysis = (uuid: string) =>
  api.get(`/projects/${uuid}/analysis`).then((r) => r.data.data.analysis as ProjectAnalysis | null);

export type FilePreview = {
  id: string; filename: string; slot: string;
  mimeType: string; sizeBytes: number; language: string;
  summary: string; preview: string;
  totalChars: number; chunkCount: number;
};

export const getFilePreview = (mongoDocId: string) =>
  api.get(`/files/${mongoDocId}/preview`).then((r) => r.data.data as FilePreview);

export const listAllArtifacts = (params?: { type?: "PPTX" | "XLSX"; page?: number; size?: number }) =>
  api.get("/artifacts", { params }).then((r) => r.data.data as {
    items: ArtifactItem[]; page: number; size: number; total: number;
  });

export const downloadArtifact = (id: number) =>
  api.get(`/artifacts/${id}/download`, { responseType: "blob" });

// 산출물 미리보기
export type PptxSlide = { index: number; title: string; bullets: string[]; speakerNote: string };
export type XlsxSheet = { name: string; totalRows: number; totalCols: number; shownRows: number; rows: string[][] };

export type ArtifactPreview =
  | {
      id: number; filename: string; type: "PPTX"; version: number;
      sizeBytes: number; createdAt: string | null;
      format: "PPTX"; totalSlides: number; shownSlides: number;
      slides: PptxSlide[];
    }
  | {
      id: number; filename: string; type: "XLSX"; version: number;
      sizeBytes: number; createdAt: string | null;
      format: "XLSX"; totalSheets: number; shownSheets: number;
      limit: { rows: number; cols: number; sheets: number };
      sheets: XlsxSheet[];
    };

export const getArtifactPreview = (id: number) =>
  api.get(`/artifacts/${id}/preview`).then((r) => r.data.data as ArtifactPreview);

export const deleteArtifact = (id: number) =>
  api.delete(`/artifacts/${id}`).then((r) => r.data);

// 산출물 인라인 편집
export type PptxSlideEditIn = {
  index: number;
  title?: string | null;
  bullets?: string[] | null;
  speakerNote?: string | null;
};
export type XlsxCellEditIn = { sheet: string; row: number; col: number; value: string };

export type ArtifactEditResult = {
  id: number; type: "PPTX" | "XLSX"; version: number; filename: string;
  sizeBytes: number; applied: any;
  fromArtifactId: number; fromVersion: number;
};

export const editArtifact = (id: number, body: {
  pptxEdits?: PptxSlideEditIn[];
  xlsxEdits?: XlsxCellEditIn[];
  note?: string;
}) =>
  api.post(`/artifacts/${id}/edit`, body).then((r) => r.data.data as ArtifactEditResult);

// ── settings / AI keys ────────────────────────────────────
export type AiSetting = {
  id: number;
  provider: "OPENAI" | "GEMINI" | "ANTHROPIC";
  alias: string | null;
  keyPreview: string;
  defaultModel: string | null;
  temperature: number | null;
  maxTokens: number | null;
  isActive: boolean;
  lastVerifiedAt: string | null;
  createdAt: string | null;
};

export type AiSettingIn = {
  provider: AiSetting["provider"];
  alias?: string;
  apiKey: string;
  defaultModel?: string;
  temperature?: number;
  maxTokens?: number;
  isActive?: boolean;
};

export type AiSettingPatch = Partial<Omit<AiSettingIn, "provider">>;

export const listAiSettings = () =>
  api.get("/settings/ai").then((r) => r.data.data.items as AiSetting[]);

export const getActiveAiSetting = (provider?: string) =>
  api.get("/settings/ai/active", { params: provider ? { provider } : undefined })
    .then((r) => r.data.data.setting as AiSetting | null);

export const createAiSetting = (body: AiSettingIn) =>
  api.post("/settings/ai", body).then((r) => r.data.data as AiSetting);

export const updateAiSetting = (id: number, body: AiSettingPatch) =>
  api.put(`/settings/ai/${id}`, body).then((r) => r.data.data as AiSetting);

export const deleteAiSetting = (id: number) =>
  api.delete(`/settings/ai/${id}`).then((r) => r.data);

export const testAiSetting = (id: number) =>
  api.post(`/settings/ai/${id}/test`).then((r) => r.data.data as { ok: boolean; latencyMs: number; echo: string });

// ── auth/me ─────────────────────────────────────────────
export const fetchMe = () =>
  api.get("/auth/me").then((r) => r.data.data.user as { uuid: string; email: string; displayName?: string; role: string });

// ── 본인 프로필 ─────────────────────────────────────────
export type MeProfile = {
  uuid: string; email: string;
  displayName: string | null; role: "USER" | "ADMIN";
  lastLoginAt: string | null; createdAt: string | null;
};

export const getMyProfile = () =>
  api.get("/users/me").then((r) => r.data.data.user as MeProfile);

export const updateMyProfile = (body: { displayName?: string }) =>
  api.put("/users/me", body).then((r) => r.data.data.user as MeProfile);

export const changeMyPassword = (currentPassword: string, newPassword: string) =>
  api.put("/users/me/password", { currentPassword, newPassword }, { silent: true } as any)
    .then((r) => r.data.data as { ok: boolean });

// ── admin: stats ────────────────────────────────────────
export type AdminStats = {
  users: number; projects: number; artifacts: number;
  llmCalls: number; categories: number; auditEntries: number;
};
export const adminStats = () =>
  api.get("/admin/stats").then((r) => r.data.data as AdminStats);

// ── admin: users ────────────────────────────────────────
export type AdminUser = {
  id: number; uuid: string; email: string; displayName?: string;
  role: "USER" | "ADMIN";
  lastLoginAt: string | null; createdAt: string | null;
};
export const adminListUsers = (params?: { q?: string; page?: number; size?: number }) =>
  api.get("/admin/users", { params }).then((r) => r.data.data as {
    items: AdminUser[]; page: number; size: number; total: number;
  });

export const adminUpdateUser = (id: number, role: "USER" | "ADMIN") =>
  api.put(`/admin/users/${id}`, { role }).then((r) => r.data.data);

export const adminDeleteUser = (id: number) =>
  api.delete(`/admin/users/${id}`).then((r) => r.data.data);

// ── admin: audit ────────────────────────────────────────
export type AuditEntry = {
  id: number; userId: number | null; action: string;
  targetType: string | null; targetUuid: string | null;
  ip?: string; userAgent?: string; meta?: any;
  createdAt: string | null;
};
export const adminListAudit = (params?: { action?: string; page?: number; size?: number }) =>
  api.get("/admin/audit", { params }).then((r) => r.data.data as {
    items: AuditEntry[]; page: number; size: number; total: number;
  });

// ── admin: category ────────────────────────────────────
export type Category = {
  id: number; code: string; nameKo: string;
  parentId: number | null; sortOrder: number;
  slideTemplateKey: string | null; systemPrompt: string | null;
  isActive: boolean;
  createdAt: string | null; updatedAt: string | null;
};
export const adminListCategories = (includeInactive = true) =>
  api.get("/admin/category", { params: { includeInactive } }).then((r) => r.data.data.items as Category[]);

export type CategoryIn = {
  code: string; nameKo: string;
  parentId?: number; sortOrder?: number;
  slideTemplateKey?: string; systemPrompt?: string;
  isActive?: boolean;
};
export const adminCreateCategory = (body: CategoryIn) =>
  api.post("/admin/category", body).then((r) => r.data.data as Category);

export type CategoryPatch = Partial<Omit<CategoryIn, "code">>;
export const adminUpdateCategory = (code: string, body: CategoryPatch) =>
  api.put(`/admin/category/${code}`, body).then((r) => r.data.data as Category);

export const adminDeleteCategory = (code: string) =>
  api.delete(`/admin/category/${code}`).then((r) => r.data.data);

// ── admin: jobs ─────────────────────────────────────────
export type JobRun = {
  at: string; status: "OK" | "ERROR" | "RUNNING";
  durationMs: number | null;
  result: any;
  error: string | null;
};

export type JobItem = {
  id: string; label: string; description: string;
  intervalMin: number;
  nextRunAt: string | null;
  paused: boolean;
  history: JobRun[];
};

export const adminListJobs = () =>
  api.get("/admin/jobs").then((r) => r.data.data.items as JobItem[]);

export const adminRunJob = (id: string) =>
  api.post(`/admin/jobs/${id}/run`).then((r) => r.data.data as { id: string; lastRun: JobRun });

export const adminPauseJob = (id: string) =>
  api.put(`/admin/jobs/${id}/pause`).then((r) => r.data.data);

export const adminResumeJob = (id: string) =>
  api.put(`/admin/jobs/${id}/resume`).then((r) => r.data.data);

// ── 알림 ─────────────────────────────────────────────────
export type NotifType = "GENERATE" | "JOB" | "SYSTEM" | "PROJECT";
export type NotifLevel = "INFO" | "SUCCESS" | "WARN" | "ERROR";

export type Notification = {
  id: number;
  type: NotifType;
  level: NotifLevel;
  title: string;
  message: string | null;
  link: string | null;
  meta: any;
  readAt: string | null;
  createdAt: string | null;
};

export const listNotifications = (params?: { onlyUnread?: boolean; page?: number; size?: number }) =>
  api.get("/notifications", { params }).then((r) => r.data.data as {
    items: Notification[]; page: number; size: number; total: number;
  });

export const fetchUnreadCount = () =>
  api.get("/notifications/unread-count", { silent: true } as any)
    .then((r) => r.data.data.count as number);

export const markNotificationRead = (id: number) =>
  api.post(`/notifications/${id}/read`).then((r) => r.data.data);

export const markAllNotificationsRead = () =>
  api.post("/notifications/read-all").then((r) => r.data.data as { updated: number });

export const deleteNotification = (id: number) =>
  api.delete(`/notifications/${id}`).then((r) => r.data.data);

export const deleteAllReadNotifications = () =>
  api.delete("/notifications").then((r) => r.data.data as { deleted: number });

// ── 협업: 공유 ───────────────────────────────────────────
export type ShareRole = "READ" | "EDIT";

export type ShareItem = {
  id: number;
  userId: number;
  userEmail: string | null;
  userDisplayName: string | null;
  role: ShareRole;
  grantedBy: number | null;
  createdAt: string | null;
};

export const listProjectShares = (uuid: string) =>
  api.get(`/projects/${uuid}/shares`).then((r) => r.data.data as {
    items: ShareItem[]; owner: { id: number };
  });

export const addProjectShare = (uuid: string, body: { email: string; role: ShareRole }) =>
  api.post(`/projects/${uuid}/shares`, body).then((r) => r.data.data as ShareItem);

export const updateProjectShare = (uuid: string, shareId: number, role: ShareRole) =>
  api.put(`/projects/${uuid}/shares/${shareId}`, { role }).then((r) => r.data.data as ShareItem);

export const deleteProjectShare = (uuid: string, shareId: number) =>
  api.delete(`/projects/${uuid}/shares/${shareId}`).then((r) => r.data.data);

export type SharedProjectItem = {
  uuid: string; projectName: string;
  companyName: string | null; status: string;
  ownerEmail: string;
  role: ShareRole;
  sharedAt: string | null;
};

export const listSharedProjects = (params?: { page?: number; size?: number }) =>
  api.get("/shared-projects", { params }).then((r) => r.data.data as {
    items: SharedProjectItem[]; page: number; size: number; total: number;
  });

// ── 협업: 댓글 ───────────────────────────────────────────
export type CommentItem = {
  id: number;
  userId: number;
  userEmail: string | null;
  userDisplayName: string | null;
  body: string;
  parentId: number | null;
  createdAt: string | null;
  updatedAt: string | null;
};

export const listProjectComments = (uuid: string) =>
  api.get(`/projects/${uuid}/comments`).then((r) => r.data.data.items as CommentItem[]);

export const addProjectComment = (uuid: string, body: string, parentId?: number) =>
  api.post(`/projects/${uuid}/comments`, { body, parentId }).then((r) => r.data.data as CommentItem);

export const deleteProjectComment = (uuid: string, commentId: number) =>
  api.delete(`/projects/${uuid}/comments/${commentId}`).then((r) => r.data.data);

// ── 백업 ────────────────────────────────────────────────
export const exportProjectZip = (uuid: string) =>
  api.get(`/projects/${uuid}/export`, { responseType: "blob" });

export const exportAllProjectsZip = () =>
  api.get("/me/export-all", { responseType: "blob" });

export const getExportSummary = () =>
  api.get("/me/export-summary").then((r) => r.data.data as {
    projectCount: number;
    projects: { uuid: string; name: string; status: string }[];
  });
