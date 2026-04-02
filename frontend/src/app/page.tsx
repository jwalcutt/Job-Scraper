import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <div className="animate-fade-in">
        <p className="text-sm font-semibold uppercase tracking-wider text-brand-600 mb-3">AI-Powered Job Matching</p>
        <h1 className="text-5xl font-extrabold tracking-tight text-gray-900 sm:text-6xl">
          Job Matcher
        </h1>
        <p className="mt-5 max-w-lg text-lg text-gray-500 leading-relaxed">
          Upload your resume, set your preferences, and let AI surface the best
          matching roles from thousands of companies and job boards.
        </p>
        <div className="mt-10 flex gap-4 justify-center">
          <Link
            href="/register"
            className="rounded-xl bg-brand-600 px-7 py-3 text-sm font-semibold text-white hover:bg-brand-700 transition-colors shadow-sm"
          >
            Get started
          </Link>
          <Link
            href="/login"
            className="rounded-xl border border-gray-200 bg-white px-7 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors shadow-card"
          >
            Sign in
          </Link>
        </div>
      </div>
    </main>
  );
}
