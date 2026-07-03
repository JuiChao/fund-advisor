export async function onRequest(context) {
    if (context.request.method !== 'POST') {
        return new Response(JSON.stringify({ error: 'Method Not Allowed' }), { 
            status: 405, 
            headers: { 'Content-Type': 'application/json' }
        });
    }

    const githubPat = context.env.GITHUB_PAT;
    if (!githubPat) {
        return new Response(JSON.stringify({ error: '未配置 GITHUB_PAT 环境变量。请在 Cloudflare Pages 后台添加。' }), { 
            status: 500,
            headers: { 'Content-Type': 'application/json' }
        });
    }

    try {
        const response = await fetch('https://api.github.com/repos/JuiChao/fund-advisor/actions/workflows/scrape.yml/dispatches', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${githubPat}`,
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Cloudflare-Pages-Fund-Advisor',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ref: 'master' })
        });

        if (response.ok) {
            return new Response(JSON.stringify({ success: true, message: 'Update triggered successfully.' }), {
                headers: { 'Content-Type': 'application/json' }
            });
        } else {
            const errorText = await response.text();
            return new Response(JSON.stringify({ error: `GitHub API Error (${response.status}): ${errorText}` }), {
                status: response.status,
                headers: { 'Content-Type': 'application/json' }
            });
        }
    } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), {
            status: 500,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}
