import styles from "./Skeleton.module.css";

interface SkeletonProps {
  width?: string;
  height?: string;
  radius?: string;
}

export function Skeleton({ width, height, radius }: SkeletonProps) {
  return (
    <div className={styles.skeleton} aria-hidden="true"
      style={{ width, height, borderRadius: radius }} />
  );
}

export function SkeletonText({ lines = 3 }: { lines?: number }) {
  const cantidad = Number.isFinite(lines) ? Math.max(0, Math.floor(lines)) : 3;
  return (
    <div className={styles.texto} aria-hidden="true">
      {Array.from({ length: cantidad }, (_, index) => (
        <Skeleton key={index} height="var(--text-base)" />
      ))}
    </div>
  );
}
