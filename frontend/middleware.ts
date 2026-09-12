import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public paths that don't require authentication
  const publicPaths = [
    "/", "/dashboard", "/pricing", "/admin",
    "/terms", "/privacy", "/cookies", "/security", "/acceptable-use", "/contact",
  ];

  // Check if the path is public
  const isPublicPath = publicPaths.some((path) => pathname === path || pathname.startsWith(path + "/"));

  // Check if it's a static asset or API route
  const isStaticAsset = pathname.startsWith("/_next/") || pathname.startsWith("/static/") || pathname.includes(".");

  if (isPublicPath || isStaticAsset) {
    return NextResponse.next();
  }

  // For dashboard routes, check for auth token
  // Since we use localStorage on the client, we need to check for a cookie
  // that mirrors the localStorage token, or we'll do the check client-side
  // The middleware will just ensure the route is accessible, and the client-side
  // auth check in the page components will handle the redirect

  // We can set a cookie when the user logs in to make this work server-side
  // For now, we'll let the client-side auth handle it and just add a header
  // to indicate this is a protected route

  const response = NextResponse.next();
  response.headers.set("x-protected-route", "true");
  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)",
  ],
};