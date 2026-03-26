import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
        Job Matcher
      </h1>
      <p className="mt-4 max-w-xl text-lg text-gray-600">
        Upload your resume, set your preferences, and let AI surface the best
        matching roles from thousands of companies and job boards — updated daily.
      </p>
      <div className="mt-8 flex gap-4">
        <Link
          href="/register"
          className="rounded-lg bg-brand-600 px-6 py-3 text-sm font-semibold text-white hover:bg-brand-700 transition-colors"
        >
          Get started
        </Link>
        <Link
          href="/login"
          className="rounded-lg border border-gray-300 px-6 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-100 transition-colors"
        >
          Sign in
        </Link>
      </div>
    </main>
  );
}
