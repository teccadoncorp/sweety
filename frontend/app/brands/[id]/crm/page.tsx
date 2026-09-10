"use client";

import { useParams } from "next/navigation";
import { CrmApp } from "@/components/crm/CrmApp";

export default function CrmPage() {
  const { id } = useParams<{ id: string }>();
  return <CrmApp brandId={id} />;
}
