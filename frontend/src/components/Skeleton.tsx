export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-card">
      <div className="flex items-start gap-3">
        {/* Avatar skeleton */}
        <div className="w-9 h-9 rounded-full animate-shimmer shrink-0" />
        <div className="flex-1 min-w-0 space-y-2.5">
          <div className="flex items-center gap-2">
            <div className="h-4 w-48 rounded animate-shimmer" />
            <div className="h-5 w-12 rounded-full animate-shimmer" />
          </div>
          <div className="h-3.5 w-36 rounded animate-shimmer" />
          <div className="h-3 w-64 rounded animate-shimmer" />
        </div>
      </div>
    </div>
  );
}

export function SkeletonList({ count = 6 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
