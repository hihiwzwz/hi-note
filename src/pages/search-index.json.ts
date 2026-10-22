import { getPosts, plainText } from '../posts';
export async function GET() {
  const posts = await getPosts();
  return new Response(JSON.stringify(posts.map((post) => ({
    id: post.id,
    title: post.data.title,
    description: post.data.description,
    body: plainText(post.body),
  }))), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
}
