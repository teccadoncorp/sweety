"use client";

import { createContext, useContext, useEffect, useState } from "react";

export const DEFAULT_APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || "Sweety";

const BrandingContext = createContext({ appName: DEFAULT_APP_NAME });

export function BrandingProvider({ children }: { children: React.ReactNode }) {
  const [appName, setAppName] = useState(DEFAULT_APP_NAME);

  useEffect(() => {
    fetch("/health")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.name && typeof data.name === "string") setAppName(data.name);
      })
      .catch(() => undefined);
  }, []);

  return <BrandingContext.Provider value={{ appName }}>{children}</BrandingContext.Provider>;
}

export function useAppName() {
  return useContext(BrandingContext).appName;
}
