// Main JavaScript for NHL MySQL Sync web interface

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Socket.IO connection if available
    if (typeof io !== 'undefined') {
        const socket = io();
        
        socket.on('connect', function() {
            console.log('Connected to server');
        });
        
        socket.on('disconnect', function() {
            console.log('Disconnected from server');
        });
        
        // Listen for sync updates
        socket.on('sync_update', function(data) {
            // This will be handled by page-specific scripts
            console.log('Sync update received:', data);
        });
        
        // Listen for log messages
        socket.on('log_message', function(data) {
            // This will be handled by page-specific scripts
            console.log('Log message received:', data);
        });
    }
});