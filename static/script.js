// script.js
document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = 'http://127.0.0.1:5000/api';

    // Get elements for login page
    const loginPage = document.getElementById('login-page');
    const emailField = document.getElementById('email-field');
    const displayEmailField = document.getElementById('display-email-field');
    const sendOtpButton = document.getElementById('send-otp-button');
    const otpInputSection = document.getElementById('otp-input-section');
    const otpField = document.getElementById('otp-field');
    const verifyOtpButton = document.getElementById('verify-otp-button');
    const messageDisplay = document.getElementById('message');

    // Get elements for dashboard page
    const dashboardPage = document.getElementById('dashboard-page');
    const logoutButton = document.getElementById('logout-button');
    const totalDonorsDisplay = document.getElementById('total-donors');
    const ngoListContainer = document.getElementById('ngo-list');

    // Get elements for NGO details page
    const ngoDetailsPage = document.getElementById('ngo-details-page');
    const backToNgosButton = document.getElementById('back-to-ngos-button');
    const ngoDetailsTitle = document.getElementById('ngo-details-title');
    const ngoRequirementsSections = document.getElementById('ngo-requirements-sections');
    const originalCostField = document.getElementById('original-cost-field');
    const purchaseYearField = document.getElementById('purchase-year-field');
    const donateButton = document.getElementById('donate-button');
    const giveawayButton = document.getElementById('giveaway-button');
    const resaleButton = document.getElementById('resale-button');
    const actionMessageDisplay = document.getElementById('action-message');

    let currentLoggedInEmail = localStorage.getItem('userEmail');
    let currentSelectedNgoId = null;
    let selectedItemsForDonation = {}; // {category: [item1, item2]}

    // --- Navigation/Page Switching Functions ---
    function showPage(pageId) {
        // Hide all main pages
        loginPage.classList.add('hidden');
        dashboardPage.classList.add('hidden', 'flex-col');
        ngoDetailsPage.classList.add('hidden', 'flex-col');

        // Show the requested page
        const pageToShow = document.getElementById(pageId);
        if (pageToShow) {
            pageToShow.classList.remove('hidden');
            if (pageId === 'dashboard-page' || pageId === 'ngo-details-page') {
                pageToShow.classList.add('flex-col'); // Ensure flex-col for layout
            }
        }
    }

    function navigateTo(hash) {
        window.location.hash = hash;
    }

    function handleHashChange() {
        const hash = window.location.hash;
        if (hash.startsWith('#ngo-details/')) {
            const ngoId = parseInt(hash.split('/')[1]);
            if (!isNaN(ngoId) && currentLoggedInEmail) {
                currentSelectedNgoId = ngoId;
                showNgoDetailsPage(ngoId);
            } else {
                navigateTo(''); // Redirect to login if not logged in or invalid NGO ID
                showLoginPage('Please log in first to view NGO details.');
            }
        } else if (hash === '#dashboard') {
            if (currentLoggedInEmail) {
                showDashboardPage();
            } else {
                navigateTo('');
                showLoginPage('Please log in to access the dashboard.');
            }
        } else {
            showLoginPage();
        }
    }

    // --- Login Page Logic ---
    function showLoginPage(msg = '') {
        showPage('login-page');
        messageDisplay.textContent = msg;
        messageDisplay.className = `mt-4 text-center font-medium ${msg.includes('successful') ? 'text-green-600' : 'text-red-600'}`;
        emailField.value = '';
        otpField.value = '';
        otpInputSection.classList.add('hidden');
        sendOtpButton.textContent = 'Click to Verify Email';
        sendOtpButton.disabled = false;
    }

    sendOtpButton.addEventListener('click', async () => {
        const email = emailField.value.trim();
        if (!email) {
            messageDisplay.textContent = 'Email is required.';
            messageDisplay.className = 'mt-4 text-center font-medium text-red-600';
            return;
        }

        sendOtpButton.textContent = 'Sending OTP...';
        sendOtpButton.disabled = true;
        messageDisplay.textContent = '';

        try {
            const response = await fetch(`${API_BASE_URL}/login/send_otp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            const data = await response.json();

            if (response.ok) {
                messageDisplay.textContent = data.message + " (Check backend console for OTP)";
                messageDisplay.className = 'mt-4 text-center font-medium text-green-600';
                displayEmailField.value = email; // Show email in OTP section
                otpInputSection.classList.remove('hidden');
            } else {
                messageDisplay.textContent = data.message;
                messageDisplay.className = 'mt-4 text-center font-medium text-red-600';
            }
        } catch (error) {
            console.error('Error sending OTP:', error);
            messageDisplay.textContent = 'Failed to connect to server. Please try again.';
            messageDisplay.className = 'mt-4 text-center font-medium text-red-600';
        } finally {
            sendOtpButton.textContent = 'Click to Verify Email';
            sendOtpButton.disabled = false;
        }
    });

    verifyOtpButton.addEventListener('click', async () => {
        const email = displayEmailField.value.trim(); // Use email from display field
        const otp = otpField.value.trim();
        if (!email || !otp) {
            messageDisplay.textContent = 'Email and OTP are required.';
            messageDisplay.className = 'mt-4 text-center font-medium text-red-600';
            return;
        }

        verifyOtpButton.textContent = 'Verifying...';
        verifyOtpButton.disabled = true;
        messageDisplay.textContent = '';

        try {
            const response = await fetch(`${API_BASE_URL}/login/verify_otp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, otp })
            });
            const data = await response.json();

            if (response.ok) {
                messageDisplay.textContent = data.message;
                messageDisplay.className = 'mt-4 text-center font-medium text-green-600';
                localStorage.setItem('userEmail', email); // Store user email on successful login
                currentLoggedInEmail = email;
                navigateTo('#dashboard'); // Go to dashboard
            } else {
                messageDisplay.textContent = data.message;
                messageDisplay.className = 'mt-4 text-center font-medium text-red-600';
            }
        } catch (error) {
            console.error('Error verifying OTP:', error);
            messageDisplay.textContent = 'Failed to connect to server. Please try again.';
            messageDisplay.className = 'mt-4 text-center font-medium text-red-600';
        } finally {
            verifyOtpButton.textContent = 'Login';
            verifyOtpButton.disabled = false;
        }
    });

    // --- Dashboard Page Logic ---
    async function showDashboardPage() {
        showPage('dashboard-page');
        await fetchTotalDonors();
        await fetchNgos();
    }

    logoutButton.addEventListener('click', () => {
        localStorage.removeItem('userEmail');
        currentLoggedInEmail = null;
        navigateTo(''); // Go back to login page
        showLoginPage('You have been logged out.');
    });

    async function fetchTotalDonors() {
        try {
            const response = await fetch(`${API_BASE_URL}/donors/total`);
            const data = await response.json();
            if (response.ok) {
                totalDonorsDisplay.textContent = data.total_donors;
            } else {
                console.error('Failed to fetch total donors:', data.message);
                totalDonorsDisplay.textContent = 'Error';
            }
        } catch (error) {
            console.error('Error fetching total donors:', error);
            totalDonorsDisplay.textContent = 'Error';
        }
    }

    async function fetchNgos() {
        ngoListContainer.innerHTML = '<div class="col-span-full text-center text-gray-600">Loading NGOs...</div>';
        try {
            const response = await fetch(`${API_BASE_URL}/ngos`);
            const ngos = await response.json();

            if (response.ok) {
                ngoListContainer.innerHTML = ''; // Clear loading message
                if (ngos.length === 0) {
                    ngoListContainer.innerHTML = '<div class="col-span-full text-center text-gray-600">No NGOs found.</div>';
                    return;
                }
                ngos.forEach(ngo => {
                    const ngoElement = document.createElement('a');
                    ngoElement.href = `#ngo-details/${ngo.id}`;
                    ngoElement.className = 'flex items-center bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-all duration-200 ease-in-out overflow-hidden';
                    ngoElement.innerHTML = `
                        <img src="${ngo.logo_url}" alt="${ngo.name} logo" class="w-24 h-24 object-cover rounded-l-lg flex-shrink-0" onerror="this.onerror=null;this.src='https://placehold.co/100x100/CCCCCC/000000?text=Logo';" />
                        <div class="p-4 flex-grow">
                            <h3 class="text-xl font-semibold text-gray-800">${ngo.name}</h3>
                            <p class="text-sm text-gray-600 line-clamp-2">${ngo.description || ''}</p>
                        </div>
                    `;
                    // Attach click listener for immediate navigation (hash change handles page display)
                    ngoElement.addEventListener('click', (event) => {
                         // Check if user is logged in before allowing navigation to NGO details
                        if (!currentLoggedInEmail) {
                            event.preventDefault(); // Prevent default link behavior
                            navigateTo(''); // Redirect to login
                            showLoginPage('Please log in first to view NGO details.');
                        }
                        // If logged in, let the hashchange event handle it
                    });
                    ngoListContainer.appendChild(ngoElement);
                });
            } else {
                ngoListContainer.innerHTML = `<div class="col-span-full text-center text-red-600">Error loading NGOs: ${ngos.message}</div>`;
            }
        } catch (error) {
            console.error('Error fetching NGOs:', error);
            ngoListContainer.innerHTML = '<div class="col-span-full text-center text-red-600">Failed to connect to server to load NGOs.</div>';
        }
    }

    // --- NGO Details Page Logic ---
    async function showNgoDetailsPage(ngoId) {
        showPage('ngo-details-page');
        ngoDetailsTitle.textContent = 'Loading NGO Details...';
        ngoRequirementsSections.innerHTML = '<div class="text-center text-gray-600">Loading requirements...</div>';
        actionMessageDisplay.textContent = ''; // Clear previous action message
        originalCostField.value = '';
        purchaseYearField.value = '';
        selectedItemsForDonation = {}; // Reset selected items

        try {
            const response = await fetch(`${API_BASE_URL}/ngo_requirements/${ngoId}`);
            const data = await response.json();

            if (response.ok) {
                ngoDetailsTitle.textContent = `${data.ngo_name} - Requirements`;
                ngoRequirementsSections.innerHTML = ''; // Clear loading message

                if (Object.keys(data.requirements).length === 0) {
                    ngoRequirementsSections.innerHTML = '<div class="text-center text-gray-600">No specific requirements listed for this NGO.</div>';
                    return;
                }

                for (const category in data.requirements) {
                    const categoryDiv = document.createElement('div');
                    categoryDiv.className = 'mb-6 bg-gray-50 p-4 rounded-lg shadow-sm';
                    categoryDiv.innerHTML = `<h3 class="text-xl font-semibold text-gray-700 mb-3">${category}</h3><div class="flex flex-wrap gap-3"></div>`;
                    
                    const itemsDiv = categoryDiv.querySelector('div.flex-wrap');
                    data.requirements[category].forEach(item => {
                        const itemContainer = document.createElement('div');
                        itemContainer.className = 'flex items-center';
                        itemContainer.innerHTML = `
                            <input type="checkbox" id="item-${category}-${item.replace(/\s/g, '-')}" data-category="${category}" data-item="${item}" class="form-checkbox h-5 w-5 text-blue-600 rounded focus:ring-blue-500" />
                            <label for="item-${category}-${item.replace(/\s/g, '-')}" class="ml-2 text-gray-700 text-lg cursor-pointer">${item}</label>
                        `;
                        itemsDiv.appendChild(itemContainer);

                        const checkbox = itemContainer.querySelector('input[type="checkbox"]');
                        checkbox.addEventListener('change', (event) => {
                            const cat = event.target.dataset.category;
                            const it = event.target.dataset.item;
                            if (event.target.checked) {
                                if (!selectedItemsForDonation[cat]) {
                                    selectedItemsForDonation[cat] = [];
                                }
                                selectedItemsForDonation[cat].push(it);
                            } else {
                                if (selectedItemsForDonation[cat]) {
                                    selectedItemsForDonation[cat] = selectedItemsForDonation[cat].filter(i => i !== it);
                                    if (selectedItemsForDonation[cat].length === 0) {
                                        delete selectedItemsForDonation[cat];
                                    }
                                }
                            }
                            updateActionButtonsState();
                        });
                    });
                    ngoRequirementsSections.appendChild(categoryDiv);
                }
                updateActionButtonsState(); // Set initial state of buttons
            } else {
                ngoDetailsTitle.textContent = 'Error';
                ngoRequirementsSections.innerHTML = `<div class="text-center text-red-600">Error loading NGO requirements: ${data.message}</div>`;
            }
        } catch (error) {
            console.error('Error fetching NGO details:', error);
            ngoDetailsTitle.textContent = 'Error';
            ngoRequirementsSections.innerHTML = '<div class="text-center text-red-600">Failed to connect to server to load NGO requirements.</div>';
        }
    }

    backToNgosButton.addEventListener('click', () => {
        navigateTo('#dashboard');
    });

    function updateActionButtonsState() {
        const hasSelectedItems = Object.keys(selectedItemsForDonation).some(cat => selectedItemsForDonation[cat].length > 0);
        
        donateButton.disabled = !hasSelectedItems;
        giveawayButton.disabled = !hasSelectedItems;
        
        const isResaleValid = hasSelectedItems && originalCostField.value.trim() !== '' && purchaseYearField.value.trim() !== '';
        resaleButton.disabled = !isResaleValid;
    }

    originalCostField.addEventListener('input', updateActionButtonsState);
    purchaseYearField.addEventListener('input', updateActionButtonsState);

    async function handleDonationAction(actionType) {
        actionMessageDisplay.textContent = '';
        let buttonToDisable = null;
        if (actionType === 'donate') buttonToDisable = donateButton;
        if (actionType === 'giveaway') buttonToDisable = giveawayButton;
        if (actionType === 'resale') buttonToDisable = resaleButton;

        if (buttonToDisable) {
            buttonToDisable.textContent = 'Processing...';
            donateButton.disabled = true;
            giveawayButton.disabled = true;
            resaleButton.disabled = true;
        }

        const itemsToSubmit = [];
        for (const category in selectedItemsForDonation) {
            selectedItemsForDonation[category].forEach(item => {
                itemsToSubmit.push({ category: category, item: item, quantity: 1 }); // Assuming quantity 1
            });
        }

        if (itemsToSubmit.length === 0) {
            actionMessageDisplay.textContent = 'Please select at least one item.';
            actionMessageDisplay.className = 'mt-6 text-center font-medium text-red-600';
            if (buttonToDisable) {
                buttonToDisable.textContent = actionType.charAt(0).toUpperCase() + actionType.slice(1);
                updateActionButtonsState();
            }
            return;
        }

        const payload = {
            user_email: currentLoggedInEmail,
            ngo_id: currentSelectedNgoId,
            action_type: actionType,
            selected_items: itemsToSubmit,
        };

        if (actionType === 'resale') {
            const originalCost = originalCostField.value.trim();
            const purchaseYear = purchaseYearField.value.trim();
            if (!originalCost || !purchaseYear) {
                actionMessageDisplay.textContent = 'Original cost and purchase year are required for resale.';
                actionMessageDisplay.className = 'mt-6 text-center font-medium text-red-600';
                if (buttonToDisable) {
                    buttonToDisable.textContent = 'Resale';
                    updateActionButtonsState();
                }
                return;
            }
            payload.original_cost = parseFloat(originalCost);
            payload.purchase_year = parseInt(purchaseYear);
        }

        try {
            const response = await fetch(`${API_BASE_URL}/donate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();

            if (response.ok) {
                actionMessageDisplay.textContent = data.message;
                actionMessageDisplay.className = 'mt-6 text-center font-medium text-green-600';
                // Clear selections and reset fields after successful submission
                selectedItemsForDonation = {};
                originalCostField.value = '';
                purchaseYearField.value = '';
                // Deselect all checkboxes
                document.querySelectorAll('#ngo-requirements-sections input[type="checkbox"]').forEach(checkbox => {
                    checkbox.checked = false;
                });
                await fetchTotalDonors(); // Update donor count on dashboard
            } else {
                actionMessageDisplay.textContent = data.message;
                actionMessageDisplay.className = 'mt-6 text-center font-medium text-red-600';
            }
        } catch (error) {
            console.error('Error processing action:', error);
            actionMessageDisplay.textContent = 'Failed to connect to server. Please try again.';
            actionMessageDisplay.className = 'mt-6 text-center font-medium text-red-600';
        } finally {
            if (buttonToDisable) {
                buttonToDisable.textContent = actionType.charAt(0).toUpperCase() + actionType.slice(1);
            }
            updateActionButtonsState();
        }
    }

    donateButton.addEventListener('click', () => handleDonationAction('donate'));
    giveawayButton.addEventListener('click', () => handleDonationAction('giveaway'));
    resaleButton.addEventListener('click', () => handleDonationAction('resale'));


    // --- Initial Load and Event Listeners ---
    window.addEventListener('hashchange', handleHashChange);

    // Initial check for logged-in state and navigate
    if (currentLoggedInEmail) {
        // If already logged in, show dashboard on initial load
        if (!window.location.hash || window.location.hash === '#') {
             navigateTo('#dashboard'); // Ensure dashboard is the initial page if logged in
        } else {
            handleHashChange(); // Handle existing hash on load
        }
    } else {
        // If not logged in, always show login page
        showLoginPage();
    }
});
