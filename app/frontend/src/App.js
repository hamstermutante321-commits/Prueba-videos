import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from 'react';
export default function App() {
    const [health, setHealth] = useState('checking...');
    useEffect(() => {
        fetch('/api/health')
            .then((r) => r.json())
            .then((j) => setHealth(JSON.stringify(j)))
            .catch(() => setHealth('backend offline (vite proxy -> 127.0.0.1:8000)'));
    }, []);
    return (_jsxs("div", { style: { fontFamily: 'system-ui', padding: 24, maxWidth: 720 }, children: [_jsx("h1", { children: "StoryForge Local Studio" }), _jsx("p", { children: "Phase 1 \u2014 esqueleto frontend + backend conectados por /api." }), _jsxs("p", { children: [_jsx("strong", { children: "Backend health:" }), " ", _jsx("code", { children: health })] }), _jsxs("ol", { children: [_jsx("li", { children: "Idea Lab / \u00E1rbol de ideas (Phase 7)" }), _jsx("li", { children: "Scene Planner, Image/Motion Studio" }), _jsx("li", { children: "Voice Lab, Caption Studio, Final Render" })] })] }));
}
