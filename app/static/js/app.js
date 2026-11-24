// Client-side analytics and real-time dashboard logic
let barChart = null;
let doughnutChart = null;

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    refreshData();
    // Auto-refresh telemetry and stream every 8 seconds
    setInterval(refreshData, 8000);
});

function initCharts() {
    const barCtx = document.getElementById('barChartTrends').getContext('2d');
    barChart = new Chart(barCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Post Count',
                data: [],
                backgroundColor: 'rgba(56, 189, 248, 0.75)',
                borderColor: '#38bdf8',
                borderWidth: 1,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(51, 65, 85, 0.4)' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });

    const doughnutCtx = document.getElementById('doughnutChartSentiment').getContext('2d');
    doughnutChart = new Chart(doughnutCtx, {
        type: 'doughnut',
        data: {
            labels: ['Positive', 'Neutral', 'Negative'],
            datasets: [{
                data: [70, 20, 10],
                backgroundColor: [
                    'rgba(52, 211, 153, 0.85)',
                    'rgba(148, 163, 184, 0.85)',
                    'rgba(244, 63, 94, 0.85)'
                ],
                borderColor: '#0f172a',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#cbd5e1', boxWidth: 12 }
                }
            },
            cutout: '68%'
        }
    });
}

async function refreshData() {
    try {
        const [trendsRes, sysRes, streamRes] = await Promise.all([
            fetch('/api/trends'),
            fetch('/api/system-info'),
            fetch('/api/stream?limit=6')
        ]);

        const trendsData = await trendsRes.json();
        const sysData = await sysRes.json();
        const streamData = await streamRes.json();

        updateDashboard(trendsData, sysData, streamData);
    } catch (err) {
        console.warn("Telemetry refresh warning:", err);
    }
}

function updateDashboard(trendsData, sysData, streamData) {
    if (sysData) {
        document.getElementById('telemetry-pod').innerText = sysData.pod_name || "pod-unknown";
        document.getElementById('telemetry-cluster').innerText = sysData.cluster_env || "local";
        const storageEl = document.getElementById('telemetry-storage');
        if (sysData.redis_connected) {
            storageEl.innerText = "Redis (Active)";
            storageEl.className = "font-semibold text-emerald-400";
        } else {
            storageEl.innerText = "In-Memory Fallback";
            storageEl.className = "font-semibold text-amber-400";
        }
    }

    if (trendsData) {
        document.getElementById('stat-total-tweets').innerText = trendsData.total_tweets_analyzed || 0;
        
        const trends = trendsData.trends || [];
        if (trends.length > 0) {
            document.getElementById('stat-top-tag').innerText = trends[0].tag;
            document.getElementById('stat-top-posts').innerText = `${trends[0].post_count} posts analyzed`;

            // Calculate aggregate sentiment
            let totalPos = 0, totalNeu = 0, totalNeg = 0;
            trends.forEach(t => {
                totalPos += (t.sentiment.positive || 0);
                totalNeu += (t.sentiment.neutral || 0);
                totalNeg += (t.sentiment.negative || 0);
            });
            const sumSentiment = totalPos + totalNeu + totalNeg;
            if (sumSentiment > 0) {
                const posPct = Math.round((totalPos / sumSentiment) * 100);
                const neuPct = Math.round((totalNeu / sumSentiment) * 100);
                const negPct = Math.max(0, 100 - posPct - neuPct);

                document.getElementById('stat-sentiment').innerText = `${posPct}%`;
                document.getElementById('pct-pos').innerText = `${posPct}%`;
                document.getElementById('pct-neu').innerText = `${neuPct}%`;
                document.getElementById('pct-neg').innerText = `${negPct}%`;

                if (doughnutChart) {
                    doughnutChart.data.datasets[0].data = [posPct, neuPct, negPct];
                    doughnutChart.update();
                }
            }

            // Update Bar Chart
            if (barChart) {
                barChart.data.labels = trends.map(t => t.tag);
                barChart.data.datasets[0].data = trends.map(t => t.post_count);
                barChart.update();
            }

            // Update Leaderboard Table
            const tbody = document.getElementById('leaderboard-body');
            tbody.innerHTML = trends.map(t => `
                <tr class="hover:bg-slate-700/30 transition">
                    <td class="py-3 px-4 font-semibold text-sky-300">${t.tag}</td>
                    <td class="py-3 px-4 font-mono font-bold">${t.post_count}</td>
                    <td class="py-3 px-4 text-slate-400">${t.reach_estimate.toLocaleString()}</td>
                    <td class="py-3 px-4">
                        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-400">
                            ${t.sentiment.positive_pct}% Pos
                        </span>
                    </td>
                    <td class="py-3 px-4 text-xs text-slate-400">~${t.velocity_per_min} / min</td>
                </tr>
            `).join('');
        }
    }

    if (streamData && streamData.length > 0) {
        const streamContainer = document.getElementById('tweet-stream-container');
        streamContainer.innerHTML = streamData.map(tw => {
            const sentimentBadge = tw.sentiment === 'positive' 
                ? 'bg-emerald-500/20 text-emerald-400' 
                : (tw.sentiment === 'negative' ? 'bg-rose-500/20 text-rose-400' : 'bg-slate-500/20 text-slate-300');
            const tags = (tw.hashtags || []).map(tg => `<span class="inline-block bg-sky-500/10 text-sky-400 px-1.5 py-0.5 rounded text-[10px]">#${tg}</span>`).join(' ');

            return `
                <div class="bg-slate-900/60 border border-slate-800 rounded-lg p-3 text-xs flex flex-col justify-between">
                    <div>
                        <div class="flex justify-between text-slate-400 mb-1">
                            <span class="font-bold text-sky-400">@${tw.author}</span>
                            <span>${tw.time_str}</span>
                        </div>
                        <p class="text-slate-200 mb-2">${tw.text}</p>
                    </div>
                    <div class="flex justify-between items-center pt-2 border-t border-slate-800/80">
                        <div class="space-x-1">${tags}</div>
                        <span class="text-[10px] px-1.5 py-0.5 rounded font-semibold ${sentimentBadge}">${tw.sentiment}</span>
                    </div>
                </div>
            `;
        }).join('');
    }
}

async function submitCustomTweet(e) {
    e.preventDefault();
    const author = document.getElementById('tweet-author').value || "cloud_user";
    const text = document.getElementById('tweet-text').value;

    try {
        const res = await fetch('/api/tweets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ author, text })
        });
        if (res.ok) {
            document.getElementById('tweet-text').value = '';
            await refreshData();
        }
    } catch (err) {
        alert("Failed to submit tweet: " + err);
    }
}

async function simulateTweetsBurst(count) {
    try {
        const res = await fetch(`/api/simulate?count=${count}`, { method: 'POST' });
        if (res.ok) {
            await refreshData();
        }
    } catch (err) {
        console.error(err);
    }
}

async function triggerCpuStress() {
    const feedback = document.getElementById('stress-feedback');
    feedback.classList.remove('hidden');
    feedback.innerText = "⏳ Generating CPU spike for HPA metrics...";
    try {
        const start = performance.now();
        const res = await fetch('/api/stress', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ intensity: 450000 })
        });
        const data = await res.json();
        const elapsed = Math.round(performance.now() - start);
        feedback.innerText = `🔥 Done! Pod: ${data.pod} computed in ${data.computation_time_seconds}s (${elapsed}ms roundtrip). CPU load recorded.`;
    } catch (err) {
        feedback.innerText = "Stress test request failed: " + err;
    }
}
