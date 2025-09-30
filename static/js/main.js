// This file contains JavaScript code for client-side functionality, such as handling form submissions and updating the UI dynamically.

document.addEventListener("DOMContentLoaded", function() {
    const form = document.getElementById("join-form");
    const statusMessage = document.getElementById("status-message");

    if (form) {
        form.addEventListener("submit", function(event) {
            event.preventDefault();
            const formData = new FormData(form);
            const name = formData.get("name");
            const groupSize = formData.get("group_size");

            fetch(form.action, {
                method: "POST",
                body: new URLSearchParams({
                    name: name,
                    group_size: groupSize
                })
            })
            .then(response => response.text())
            .then(data => {
                statusMessage.innerHTML = data;
                form.reset();
            })
            .catch(error => {
                console.error("Error:", error);
                statusMessage.innerHTML = "There was an error processing your request.";
            });
        });
    }
});