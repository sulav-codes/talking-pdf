"use client";

import { Activity, Zap, DollarSign, Shield } from "lucide-react";

const features = [
  {
    icon: Zap,
    title: "Lightning Fast",
    description: "Groq LPU technology delivers 500+ tokens/sec",
    color: "text-yellow-500",
    bgColor: "bg-yellow-50 dark:bg-yellow-950/20",
  },
  {
    icon: DollarSign,
    title: "100% Free",
    description: "Local embeddings + Groq free tier = $0 cost",
    color: "text-green-500",
    bgColor: "bg-green-50 dark:bg-green-950/20",
  },
  {
    icon: Shield,
    title: "Private & Secure",
    description: "Embeddings run locally on your machine",
    color: "text-blue-500",
    bgColor: "bg-blue-50 dark:bg-blue-950/20",
  },
  {
    icon: Activity,
    title: "Production Ready",
    description: "Professional architecture with best practices",
    color: "text-purple-500",
    bgColor: "bg-purple-50 dark:bg-purple-950/20",
  },
];

export default function FeatureCards() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {features.map((feature, index) => {
        const Icon = feature.icon;
        return (
          <div
            key={index}
            className="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:shadow-lg transition-shadow"
          >
            <div
              className={`w-12 h-12 rounded-lg ${feature.bgColor} flex items-center justify-center mb-3`}
            >
              <Icon className={`w-6 h-6 ${feature.color}`} />
            </div>
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-1">
              {feature.title}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {feature.description}
            </p>
          </div>
        );
      })}
    </div>
  );
}
