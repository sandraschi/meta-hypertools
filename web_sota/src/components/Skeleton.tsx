import { motion } from "framer-motion";
import type React from "react";

interface SkeletonProps {
  className?: string;
  variant?: "text" | "rectangular" | "circular";
  width?: string | number;
  height?: string | number;
  animation?: boolean;
}

export function Skeleton({
  className = "",
  variant = "rectangular",
  width,
  height,
  animation = true,
}: SkeletonProps) {
  const baseClasses = "bg-gradient-to-r from-white/5 via-white/10 to-white/5";

  const variantClasses = {
    text: "rounded h-4",
    rectangular: "rounded-lg",
    circular: "rounded-full",
  };

  const style: React.CSSProperties = {};
  if (width) style.width = typeof width === "number" ? `${width}px` : width;
  if (height) style.height = typeof height === "number" ? `${height}px` : height;

  if (animation) {
    return (
      <motion.div
        className={`${baseClasses} ${variantClasses[variant]} ${className}`}
        style={{
          ...style,
          backgroundSize: "200% 100%",
        }}
        animate={{
          backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"],
        }}
        transition={{
          duration: 2,
          repeat: Number.POSITIVE_INFINITY,
          ease: "easeInOut",
        }}
      />
    );
  }

  return <div className={`${baseClasses} ${variantClasses[variant]} ${className}`} style={style} />;
}

interface SkeletonCardProps {
  className?: string;
}

export function SkeletonCard({ className = "" }: SkeletonCardProps) {
  return (
    <div className={`glass-panel p-4 md:p-6 ${className}`}>
      <Skeleton variant="text" height={24} width="60%" className="mb-3" />
      <Skeleton variant="text" height={16} width="100%" className="mb-2" />
      <Skeleton variant="text" height={16} width="80%" className="mb-4" />
      <Skeleton variant="rectangular" height={32} width="100%" />
    </div>
  );
}

interface SkeletonGridProps {
  count?: number;
  className?: string;
}

export function SkeletonGrid({ count = 4, className = "" }: SkeletonGridProps) {
  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 ${className}`}>
      {Array.from({ length: count }, (_, i) => (
        <motion.div
          // biome-ignore lint/suspicious/noArrayIndexKey: Purely decorative skeleton items
          key={`skeleton-grid-item-${i}`}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.1 }}
        >
          <SkeletonCard />
        </motion.div>
      ))}
    </div>
  );
}
