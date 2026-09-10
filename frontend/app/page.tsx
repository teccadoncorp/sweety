import { Inter } from "next/font/google";
import { LandingPage } from "@/components/landing/LandingPage";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export default function Home() {
  return <LandingPage fontClass={inter.className} />;
}
