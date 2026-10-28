
document.addEventListener("DOMContentLoaded", () => {
    const lavender = "#8d78df";
    const green = "#48b995";
    const pink = "#e77f9a";
    const palette = [
        "#8d78df", "#b4a4f1", "#48b995",
        "#e77f9a", "#f0bc73", "#78b8d8",
        "#a6c98c", "#c9a0dc", "#ed9e76"
    ];

    // Dashboard: expenses by category
    const categoryElement = document.getElementById("categoryData");
    const categoryCanvas = document.getElementById("categoryChart");

    if (categoryElement && categoryCanvas && window.Chart) {
        const data = JSON.parse(categoryElement.textContent);

        new Chart(categoryCanvas, {
            type: "doughnut",
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: palette,
                    borderWidth: 3,
                    borderColor: "#ffffff",
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: "70%",
                animation: {
                    animateRotate: true,
                    duration: 900
                },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            usePointStyle: true,
                            pointStyle: "circle",
                            padding: 18,
                            font: { family: "DM Sans", size: 11 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) =>
                                `${context.label}: ₹${Number(context.raw).toLocaleString("en-IN")}`
                        }
                    }
                }
            }
        });
    }

    // Analytics: monthly income versus expenses
    const monthlyElement = document.getElementById("monthlyData");
    const monthlyCanvas = document.getElementById("monthlyChart");

    if (monthlyElement && monthlyCanvas && window.Chart) {
        const data = JSON.parse(monthlyElement.textContent);

        new Chart(monthlyCanvas, {
            type: "bar",
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: "Income",
                        data: data.income,
                        backgroundColor: green,
                        borderRadius: 6
                    },
                    {
                        label: "Expenses",
                        data: data.expenses,
                        backgroundColor: pink,
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 800 },
                interaction: {
                    mode: "index",
                    intersect: false
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: "#89869b" }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: "#89869b",
                            callback: value => "₹" + value.toLocaleString("en-IN")
                        },
                        grid: { color: "#f0edf6" }
                    }
                },
                plugins: {
                    legend: {
                        position: "top",
                        align: "end",
                        labels: { usePointStyle: true, padding: 18 }
                    },
                    tooltip: {
                        callbacks: {
                            label: context =>
                                `${context.dataset.label}: ₹${Number(context.raw).toLocaleString("en-IN")}`
                        }
                    }
                }
            }
        });
    }

    // Analytics: all-time spending by category
    const analyticsElement =
        document.getElementById("analyticsCategoryData");
    const analyticsCanvas =
        document.getElementById("analyticsCategoryChart");

    if (analyticsElement && analyticsCanvas && window.Chart) {
        const data = JSON.parse(analyticsElement.textContent);

        new Chart(analyticsCanvas, {
            type: "doughnut",
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: palette,
                    borderColor: "#ffffff",
                    borderWidth: 3,
                    hoverOffset: 7
                }]
            },
            options: {
                responsive: true,
                cutout: "65%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            usePointStyle: true,
                            padding: 15
                        }
                    }
                }
            }
        });
    }
});
