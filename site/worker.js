// Static assets answer every request except the films. Safari on iOS only plays <video>
// when the server honours byte ranges (206), and the asset server returns the whole file,
// so this slices the MP4 for range requests.
export default {
  async fetch(request, env) {
    const response = await env.ASSETS.fetch(request);
    const range = request.headers.get("Range");
    if (response.status !== 200 || !(response.headers.get("Content-Type") || "").startsWith("video/")) {
      return response;
    }
    const headers = new Headers(response.headers);
    headers.set("Accept-Ranges", "bytes");
    headers.set("Cache-Control", "public, max-age=86400");
    if (!range) return new Response(response.body, { status: 200, headers });

    const body = await response.arrayBuffer();
    const size = body.byteLength;
    const match = /^bytes=(\d*)-(\d*)$/.exec(range.trim());
    if (!match || (match[1] === "" && match[2] === "")) {
      return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
    }
    let start, end;
    if (match[1] === "") {
      start = Math.max(0, size - Number(match[2]));
      end = size - 1;
    } else {
      start = Number(match[1]);
      end = match[2] === "" ? size - 1 : Math.min(Number(match[2]), size - 1);
    }
    if (start > end || start >= size) {
      return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
    }
    headers.set("Content-Range", `bytes ${start}-${end}/${size}`);
    headers.set("Content-Length", String(end - start + 1));
    return new Response(body.slice(start, end + 1), { status: 206, headers });
  },
};
