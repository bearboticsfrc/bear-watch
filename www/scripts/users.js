function formatTime(epoch) {
    const options = { timeStyle: 'short' };
    return new Date(epoch * 1000).toLocaleTimeString([], options);
}

function createUserCard(user) {
    const lastSeenTime = formatTime(user.last_seen);

    return `
        <div class="col-md-4">
            <div class="card text-dark bg-light mb-3">
                <div class="card-body">
                    <h5 class="card-title"><b>${user.name}</b></h5>
                    <p class="card-text">
                        Role: <b>${user.role}</b><br>
                        MAC Address: <b>${user.mac}</b><br>
                        Last Seen: <b>${lastSeenTime}</b>
                    </p>
                </div>
            </div>
        </div>
    `;
}

async function fetchActiveUsers() {
    const activeUsersDiv = document.getElementById('active-users');
    activeUsersDiv.innerHTML = '';

    try {
        const response = await fetch('/user');

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();
        const users = data.users || {};

        const loggedInUsers = Object.values(users).filter(user => user.logged_in);

        activeUsersDiv.innerHTML = loggedInUsers.length
            ? loggedInUsers.map(createUserCard).join('')
            : `<div class="alert alert-info text-center" role="alert">
                 No logged-in users at the moment.
               </div>`;

    } catch (error) {
        console.error('Error fetching logged-in users:', error);

        activeUsersDiv.innerHTML = `
            <div class="alert alert-danger text-center" role="alert">
                Failed to load logged-in users. Please try again later.
            </div>
        `;
    }
}

const refreshInterval = 45000; // 45 seconds
setInterval(fetchActiveUsers, refreshInterval);

document.addEventListener('DOMContentLoaded', fetchActiveUsers);
