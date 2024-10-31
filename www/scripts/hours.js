function formatHours(hours) {
    return Number.isInteger(hours) ? hours : hours.toFixed(2);
}

function createUserCard(user) {
    return `
        <div class="col-md-4">
            <div class="card text-dark bg-light mb-3 border-dark">
                <div class="card-body">
                    <h5 class="card-title"><b>${user.name}</b></h5>
                    <p class="card-text">
                        Role: <b>${user.role}</b><br>
                        Total Hours: <b>${formatHours(user.total_hours)}</b>
                    </p>
                </div>
            </div>
        </div>
    `;
}

async function fetchTotalHours() {
    const totalHoursDiv = document.getElementById('total-hours');
    totalHoursDiv.innerHTML = '';

    try {
        const response = await fetch('/hour');

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();
        const users = data.users || {};
        const sortedUsers = Object.values(users).sort((a, b) => b.total_hours - a.total_hours);

        totalHoursDiv.innerHTML = Object.values(sortedUsers).map(createUserCard).join('');
    } catch (error) {
        console.error('Error fetching total hours:', error);

        totalHoursDiv.innerHTML = `
            <div class="alert alert-danger text-center" role="alert">
                Failed to load total user hours. Please try again later.
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetchTotalHours();
});
