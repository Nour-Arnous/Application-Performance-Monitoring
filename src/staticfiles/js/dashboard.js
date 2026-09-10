// Helper function to obtain CSRF Token from browser cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Global chart instances and configuration state
let mainChart = null;
let forecastChart = null;
let errorPieChart = null;
let requestsPieChart = null;
let currentTimeRange = 24;
let ws = null;

// Initialize metrics, forecast, applications table, and WebSocket on page load
document.addEventListener('DOMContentLoaded', () => {
    setupTimeFilterListeners();
    fetchDataAndRenderCharts();
    fetchForecastData(); // Retrieves AI forecast for the available application
    fetchDashboardAlerts(); // Fetches active alerts with delete options
    fetchApplicationsTable(); // Populates applications list for admin/staff
    connectWebSocket();
});

// Setup event listeners for the time duration filter buttons (1h, 24h, 1w)
function setupTimeFilterListeners() {
    const buttons = document.querySelectorAll('.time-filter-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const currentBtn = e.currentTarget; // تم التعديل إلى currentTarget
            buttons.forEach(b => {
                b.classList.remove('active', 'btn-primary');
                b.classList.add('btn-outline-primary');
            });
            currentBtn.classList.add('active', 'btn-primary');
            currentBtn.classList.remove('btn-outline-primary');
            currentTimeRange = currentBtn.getAttribute('data-hours');
            fetchDataAndRenderCharts();
        });
    });
}

// Connect to Django Channels WebSocket for real-time live metrics streaming
function connectWebSocket() {
    const token = sessionStorage.getItem('access_token') || '';
    const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = `${wsProtocol}${window.location.host}/ws/metrics/?token=${token}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = function () {
        console.log('WebSocket connected successfully');
    };

    ws.onmessage = function (event) {
        try {
            const data = JSON.parse(event.data);
            updateChartsWithNewMetric(data);
            fetchDashboardAlerts();
        } catch (error) {
            console.error('Error processing WebSocket message:', error);
        }
    };

    ws.onclose = function () {
        console.log('WebSocket disconnected. Reconnecting in 3 seconds...');
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = function (error) {
        console.error('WebSocket error:', error);
    };
}

// Append new real-time metric point to the main line chart
function updateChartsWithNewMetric(data) {
    if (!mainChart) return;
    const time = new Date(data.timestamp).toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });

    if (mainChart.data.labels.length >= 30) {
        mainChart.data.labels.shift();
        mainChart.data.datasets.forEach(dataset => dataset.data.shift());
    }

    mainChart.data.labels.push(time);
    mainChart.data.datasets[0].data.push(data.response_time);
    mainChart.data.datasets[1].data.push(data.request_count);
    mainChart.data.datasets[2].data.push(data.error_count);
    mainChart.update();
}

// Fetch metric historical data from REST API and refresh UI cards and charts
async function fetchDataAndRenderCharts() {
    const loading = document.getElementById('loadingIndicator');
    if (loading) loading.style.display = 'block';

    try {
        const response = await fetch(`/api/metrics/?hours=${currentTimeRange}`);
        const data = await response.json();

        // Extract results list if API uses DRF pagination
        const metricsList = Array.isArray(data) ? data : (data.results || []);

        updateStatistics(metricsList);
        renderLineChart(metricsList);
        updateDashboardCharts(metricsList);

        const now = new Date();
        document.getElementById('lastUpdate').innerHTML =
            `<i class="fas fa-clock"></i> Last Update: ${now.toLocaleTimeString('ar-EG')}`;
    } catch (error) {
        console.error('Error fetching dashboard metrics:', error);
        document.getElementById('lastUpdate').innerHTML =
            `<i class="fas fa-exclamation-circle text-danger"></i> Update failed`;
    } finally {
        if (loading) loading.style.display = 'none';
    }
}

// Fetch AI Prophet Forecast data for the main dashboard
async function fetchForecastData() {
    try {
        let targetAppId = typeof appId !== 'undefined' ? appId : null;

        if (!targetAppId) {
            const appsResponse = await fetch('/api/applications/');
            if (appsResponse.ok) {
                const appsData = await appsResponse.json();
                const appsList = Array.isArray(appsData) ? appsData : (appsData.results || []);
                if (appsList.length > 0) {
                    targetAppId = appsList[0].id;
                }
            }
        }

        if (!targetAppId) {
            console.warn('No registered applications found to generate AI forecast.');
            return;
        }

        const response = await fetch(`/api/applications/${targetAppId}/forecast/`);
        if (!response.ok) return;

        const forecastData = await response.json();
        renderForecastChart(forecastData);
    } catch (error) {
        console.error('Error fetching AI forecast data:', error);
    }
}

// Update summary card statistics
function updateStatistics(data) {
    if (!data || data.length === 0) {
        document.getElementById('statAvgResponse').textContent = '0.00';
        document.getElementById('statTotalRequests').textContent = '0';
        document.getElementById('statTotalErrors').textContent = '0';
        return;
    }

    const totalResponse = data.reduce((sum, item) => sum + (item.response_time || 0), 0);
    const avg = totalResponse / data.length;
    document.getElementById('statAvgResponse').textContent = avg.toFixed(2);

    const totalRequests = data.reduce((sum, item) => sum + (item.request_count || 0), 0);
    document.getElementById('statTotalRequests').textContent = totalRequests.toLocaleString();

    const totalErrors = data.reduce((sum, item) => sum + (item.error_count || 0), 0);
    document.getElementById('statTotalErrors').textContent = totalErrors.toLocaleString();
}

// Fetch and display dashboard alerts with delete functionality
async function fetchDashboardAlerts() {
    const container = document.getElementById('alertsContainer');
    if (!container) return;

    try {
        const response = await fetch('/api/alerts/');
        if (!response.ok) throw new Error('Failed to fetch alerts');

        const data = await response.json();
        const alertsList = Array.isArray(data) ? data : (data.results || []);

        if (alertsList.length === 0) {
            container.innerHTML = `
                    <div class="alert-card success mb-0">
                        <i class="fas fa-check-circle text-success me-2"></i>
                        All applications are running normally. No active alerts.
                    </div>
                `;
            return;
        }

        container.innerHTML = alertsList.map(alertItem => {
            const alertType = alertItem.severity === 'CRITICAL' ? 'danger' : 'warning';
            const appName = alertItem.app_name || alertItem.application_name || `App #${alertItem.application || ''}`;
            const timeStr = alertItem.created_at ? new Date(alertItem.created_at).toLocaleTimeString('ar-EG') : '';

            return `
                    <div class="alert-card ${alertType} mb-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>${appName}</strong> - ${alertItem.message || 'Threshold breached'}
                                <span class="alert-time ms-2">${timeStr}</span>
                            </div>
                            <button onclick="deleteDashboardAlert(${alertItem.id})" class="btn btn-sm btn-outline-danger" title="Delete Alert">
                                <i class="fas fa-trash-alt me-1"></i> Delete
                            </button>
                        </div>
                    </div>
                `;
        }).join('');
    } catch (error) {
        console.error('Error fetching dashboard alerts:', error);
    }
}

// Delete / Dismiss Alert Function
async function deleteDashboardAlert(alertId) {
    if (!confirm('Are you sure you want to delete this alert?')) {
        return;
    }

    try {
        const response = await fetch(`/api/alerts/${alertId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        });

        if (response.ok || response.status === 204) {
            fetchDashboardAlerts();
        } else {
            alert('Failed to delete alert.');
        }
    } catch (error) {
        console.error('Error deleting alert:', error);
        alert('An error occurred while deleting the alert.');
    }
}

// Fetch and populate applications table with robust error handling
async function fetchApplicationsTable() {
    const tableBody = document.getElementById('applicationsTableBody');
    if (!tableBody) return;

    try {
        const response = await fetch('/api/applications/');

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        let appsList = [];
        if (Array.isArray(data)) {
            appsList = data;
        } else if (data && Array.isArray(data.results)) {
            appsList = data.results;
        } else if (data && Array.isArray(data.data)) {
            appsList = data.data;
        }

        const countBadge = document.getElementById('tableAppsCount');
        if (countBadge) {
            countBadge.textContent = `${appsList.length} Applications`;
        }

        if (appsList.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted py-3">No applications registered yet.</td>
                </tr>`;
            return;
        }

        tableBody.innerHTML = appsList.map((app, index) => {
            const ownerDisplay = app.owner_name || app.owner_email || (app.owner ? `User #${app.owner}` : 'N/A');
            const createdDate = app.created_at ? new Date(app.created_at).toLocaleDateString() : 'N/A';
            const appId = app.id || '';
            const appName = app.name || `App #${appId}`;

            return `
                <tr>
                    <td><strong>${index + 1}</strong></td>
                    <td><span class="fw-bold text-dark">${appName}</span></td>
                    <td>
                        <span class="badge bg-light text-dark border px-2 py-1">
                            <i class="fas fa-user text-secondary me-1"></i> ${ownerDisplay}
                        </span>
                    </td>
                    <td><small class="text-muted">${createdDate}</small></td>
                    <td>
                        <span class="badge bg-success border text-success">
                            <i class="fas fa-circle fa-xs me-1"></i> Active
                        </span>
                    </td>
                    <td class="text-center">
                        <button onclick="deleteApplication('${appId}')" class="btn btn-sm btn-outline-danger" title="Delete Application">
                            <i class="fas fa-trash-alt me-1"></i> Delete
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        console.error('Error fetching applications for table:', error);
        tableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-danger py-3">
                    <i class="fas fa-exclamation-triangle me-1"></i> Failed to load applications list.
                </td>
            </tr>`;
    }
}

// Delete Application Function
async function deleteApplication(appId) {
    if (!confirm('Are you sure you want to delete this application? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/api/applications/${appId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        });

        if (response.ok || response.status === 204) {
            alert('Application deleted successfully.');
            fetchApplicationsTable();
            fetchDataAndRenderCharts();
        } else {
            alert('Failed to delete application.');
        }
    } catch (error) {
        console.error('Error deleting application:', error);
        alert('An error occurred while deleting the application.');
    }
}

// Render multi-axis main line chart for timeline metrics
function renderLineChart(data) {
    const canvas = document.getElementById('mainLineChart');
    if (!canvas) return; // Guard clause: Ensure canvas element exists in DOM
    
    if (!Array.isArray(data) || data.length === 0) {
        console.warn('No metrics data available for line chart.');
        return; // Guard clause: Prevent errors if data is empty or invalid
    }

    const ctx = canvas.getContext('2d');
    const sorted = data.slice().sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    const labels = sorted.map(item => {
        const d = new Date(item.timestamp);
        return d.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
    });

    const responseData = sorted.map(item => item.response_time || 0);
    const requestData = sorted.map(item => item.request_count || 0);
    const errorData = sorted.map(item => item.error_count || 0);

    if (mainChart) mainChart.destroy();

    mainChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Response Time (s)',
                    data: responseData,
                    borderColor: 'rgba(9, 132, 227, 1)',
                    backgroundColor: 'rgba(9, 132, 227, 0.1)',
                    tension: 0.3,
                    yAxisID: 'y'
                },
                {
                    label: 'Requests',
                    data: requestData,
                    borderColor: 'rgba(0, 184, 148, 1)',
                    backgroundColor: 'rgba(0, 184, 148, 0.1)',
                    tension: 0.3,
                    yAxisID: 'y1'
                },
                {
                    label: 'Errors',
                    data: errorData,
                    borderColor: 'rgba(225, 112, 85, 1)',
                    backgroundColor: 'rgba(225, 112, 85, 0.1)',
                    tension: 0.3,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // Ensures flexible responsiveness inside grid/flex containers
            interaction: { mode: 'index', intersect: false },
            scales: {
                y: { type: 'linear', display: true, position: 'left', title: { display: true, text: 'Seconds' } },
                y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Count' } }
            }
        }
    });
}

// Render or update the Chart.js forecast instance
function renderForecastChart(rawData) {
    const canvas = document.getElementById('forecastChart');
    if (!canvas) return; // Guard clause: Ensure canvas element exists in DOM

    const ctx = canvas.getContext('2d');

    let forecastList = [];
    if (Array.isArray(rawData)) {
        forecastList = rawData;
    } else if (rawData && Array.isArray(rawData.forecast)) {
        forecastList = rawData.forecast;
    } else if (rawData && Array.isArray(rawData.data)) {
        forecastList = rawData.data;
    } else if (rawData && Array.isArray(rawData.results)) {
        forecastList = rawData.results;
    }

    if (!forecastList || forecastList.length === 0) {
        console.warn('No forecast records available to render.');
        return;
    }

    const labels = forecastList.map(item => {
        const timeVal = item.timestamp || item.ds;
        const dateObj = new Date(timeVal);
        return isNaN(dateObj.getTime()) ? timeVal : dateObj.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
    });

    const yhat = forecastList.map(item => Math.max(0, item.yhat || 0));
    const yhatLower = forecastList.map(item => Math.max(0, item.yhat_lower || 0));
    const yhatUpper = forecastList.map(item => Math.max(0, item.yhat_upper || 0));

    if (typeof forecastChart !== 'undefined' && forecastChart) {
        forecastChart.destroy();
    }

    forecastChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Predicted Response Time (s)',
                    data: yhat,
                    borderColor: 'rgba(108, 92, 231, 1)',
                    backgroundColor: 'rgba(108, 92, 231, 0.2)',
                    fill: false,
                    tension: 0.4
                },
                {
                    label: 'Upper Bound',
                    data: yhatUpper,
                    borderColor: 'rgba(108, 92, 231, 0.3)',
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0
                },
                {
                    label: 'Lower Bound',
                    data: yhatLower,
                    borderColor: 'rgba(108, 92, 231, 0.3)',
                    borderDash: [5, 5],
                    fill: '-1',
                    backgroundColor: 'rgba(108, 92, 231, 0.08)',
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    min: 0,
                    title: {
                        display: true,
                        text: 'Seconds'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Time'
                    }
                }
            }
        }
    });
}


// Aggregates metrics by application name and updates the pie charts
function updateDashboardCharts(metricsData) {
    if (!metricsData || metricsData.length === 0) return;

    const appRequests = {};
    const appErrors = {};
    const uniqueApps = new Set();

    metricsData.forEach(metric => {
        const appName = metric.application_name || `App #${metric.application}`;
        uniqueApps.add(appName);

        appRequests[appName] = (appRequests[appName] || 0) + (metric.request_count || 0);
        appErrors[appName] = (appErrors[appName] || 0) + (metric.error_count || 0);
    });

    const appCountElement = document.getElementById('statApps');
    if (appCountElement) {
        appCountElement.innerText = uniqueApps.size;
    }

    const appLabels = Object.keys(appRequests);
    const requestValues = Object.values(appRequests);
    const errorValues = Object.values(appErrors);

    const chartColors = [
        '#0984e3', '#00b894', '#fdcb6e', '#e17055',
        '#6c5ce7', '#e84393', '#00cec9', '#d63031'
    ];
    
    const colorsSlice = appLabels.map((_, i) => chartColors[i % chartColors.length]);

    const reqCanvas = document.getElementById('requestsPieChart');
    if (reqCanvas) {
        if (requestsPieChart) {
            requestsPieChart.data.labels = appLabels;
            requestsPieChart.data.datasets[0].data = requestValues;
            requestsPieChart.data.datasets[0].backgroundColor = colorsSlice;
            requestsPieChart.update();
        } else {
            requestsPieChart = new Chart(reqCanvas.getContext('2d'), {
                type: 'pie',
                data: {
                    labels: appLabels,
                    datasets: [{ data: requestValues, backgroundColor: colorsSlice }]
                },
                options: { responsive: true }
            });
        }
    }

    const errCanvas = document.getElementById('errorPieChart');
    if (errCanvas) {
        if (errorPieChart) {
            errorPieChart.data.labels = appLabels;
            errorPieChart.data.datasets[0].data = errorValues;
            errorPieChart.data.datasets[0].backgroundColor = colorsSlice;
            errorPieChart.update();
        } else {
            errorPieChart = new Chart(errCanvas.getContext('2d'), {
                type: 'pie',
                data: {
                    labels: appLabels,
                    datasets: [{ data: errorValues, backgroundColor: colorsSlice }]
                },
                options: { responsive: true }
            });
        }
    }
}