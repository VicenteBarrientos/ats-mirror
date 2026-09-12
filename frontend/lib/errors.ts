export class ApiError extends Error {
  readonly status: number;
  readonly offline: boolean;

  constructor(message: string, status = 0, offline = false) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.offline = offline;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export function userFacingError(error: unknown): string {
  if (isApiError(error)) {
    return error.message;
  }
  return "ATS Mirror API is unavailable.";
}
