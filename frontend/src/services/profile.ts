import { api } from "./api";
import type { Profile } from "@/types/profile";

export async function fetchProfile(): Promise<Profile> {
  const { data } = await api.get<Profile>("/profile");
  return data;
}

export async function updateProfile(payload: Partial<Profile>): Promise<Profile> {
  const { data } = await api.put<Profile>("/profile", payload);
  return data;
}

/** Generic CRUD for a profile child collection (education/experience/projects/certifications/skills). */
export function childCollectionApi<T extends { id: string }>(path: string) {
  return {
    list: async (): Promise<T[]> => (await api.get<T[]>(`/profile/${path}`)).data,
    create: async (payload: Partial<T>): Promise<T> =>
      (await api.post<T>(`/profile/${path}`, payload)).data,
    update: async (id: string, payload: Partial<T>): Promise<T> =>
      (await api.put<T>(`/profile/${path}/${id}`, payload)).data,
    remove: async (id: string): Promise<void> => {
      await api.delete(`/profile/${path}/${id}`);
    },
  };
}
