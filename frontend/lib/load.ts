export async function loadPageData<T>(
  loader: () => Promise<T>,
): Promise<{ ok: true; data: T } | { ok: false; error: unknown }> {
  try {
    return { ok: true, data: await loader() };
  } catch (error) {
    return { ok: false, error };
  }
}
