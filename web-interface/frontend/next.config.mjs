/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export for Cloudflare Pages
  output: "export",

  // Static export cannot optimize images at build time
  images: {
    unoptimized: true,
  },

  // Avoid SWC worker crash on Node 24
  experimental: {
    workerThreads: false,
  },
};

export default nextConfig;
