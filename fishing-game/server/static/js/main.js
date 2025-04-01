console.log("main.js loaded");

// --- Configuration ---
const SERVER_URL = window.location.origin; // Use the same origin as the web page
const GAME_WIDTH = 800;
const GAME_HEIGHT = 600;

// --- Socket.IO Connection ---
// Connect to the '/game' namespace defined in the backend
const socket = io(`${SERVER_URL}/game`); // Adjust namespace if different

socket.on("connect", () => {
    console.log("Connected to server via Socket.IO with SID:", socket.id);
    // Ask user for name or use a default, then join
    const playerName = prompt("Enter your player name:", `Player_${socket.id.substring(0, 4)}`);
    if (playerName) {
        socket.emit("join_game", { name: playerName });
    } else {
        console.error("No player name entered. Cannot join game.");
        // Handle this case more gracefully (e.g., show an error message)
    }
});

socket.on("disconnect", (reason) => {
    console.log("Disconnected from server:", reason);
    // Handle disconnection (e.g., show message, disable game)
});

socket.on("connect_error", (err) => {
    console.error("Connection error:", err);
    // Handle connection errors (e.g., show message)
});

socket.on("error", (data) => {
    console.error("Server error:", data.message);
    alert(`Server error: ${data.message}`); // Simple alert for now
});


// --- Phaser Game Setup ---

class MainScene extends Phaser.Scene {
    constructor() {
        super({ key: 'MainScene' });
        this.player = null; // Reference to the current player's sprite
        this.otherPlayers = {}; // Store other player graphics { id: { rect: rect, stateText: text } }
        this.fishes = {}; // Store fish graphics { id: rect }
        this.lines = {}; // Store cast line graphics { playerId: lineGraphic }
        this.playerStates = {}; // Store player states { id: state }
        this.playerDirections = {}; // Store player directions { id: direction }
        this.directionIndicator = {}; // Store direction indicators { id: graphic }
        this.cursors = null; // For movement (Arrow keys) - WILL BE REMOVED
        this.wasd = null; // For facing direction (WASD)
        this.isCharging = false;
        this.chargeStartTime = 0;
        // Visual elements
        this.chargeBar = null;
        this.chargeBarBg = null;
        this.stateText = null; // Text for our player's state
        // Hook attempt meter elements
        this.hookMeterBg = null;
        this.hookMeterThreshold = null;
        this.hookMeterRoll = null;
        this.hookMeterText = null;
    }

    preload() {
        console.log("Preloading assets...");
        // No assets to preload for simple shapes
    }

    create() {
        console.log("Creating scene...");
        // Movement keys (Will be replaced by WASD relative movement)
        this.cursors = this.input.keyboard.createCursorKeys();
        // Facing/Movement keys
        this.wasd = this.input.keyboard.addKeys({
            up: Phaser.Input.Keyboard.KeyCodes.W,
            down: Phaser.Input.Keyboard.KeyCodes.S,
            left: Phaser.Input.Keyboard.KeyCodes.A,
            right: Phaser.Input.Keyboard.KeyCodes.D,
            cancel: Phaser.Input.Keyboard.KeyCodes.C // Add C key for cancelling
        });

        this.cameras.main.setBackgroundColor('#3498db'); // Set background to blue

        // --- Input Handlers ---
        this.input.on('pointerdown', this.startCharging, this);
        this.input.on('pointerup', this.castLine, this);
        // Prevent context menu on right-click if needed
        this.input.mouse.disableContextMenu();

        // --- Socket Event Handlers ---
        // Listen for the welcome message from the server
        socket.on("welcome", (data) => {
            console.log("Received welcome:", data);
            if (data.player) {
                this.initializeSelf(data.player); // Initialize our player sprite
            } else {
                console.error("Welcome event received without player data.");
            }
        });

        socket.on("world_state", (data) => {
            console.log("Received world state (others):", data);
            this.initializeOthers(data); // Initialize other players and fish
        });

        socket.on("player_joined", (playerData) => {
            console.log("Player joined:", playerData);
            this.addOtherPlayer(playerData);
        });

        socket.on("player_left", (data) => {
            console.log("Player left:", data);
            this.removeOtherPlayer(data.id);
        });

        socket.on("player_moved", (playerData) => {
            // console.log("Player moved:", playerData); // Can be noisy
            this.updateOtherPlayerPosition(playerData);
        });

        // Listen for state changes
        socket.on("player_state_changed", (data) => {
            console.log("Player state changed:", data);
            this.updatePlayerState(data.id, data.state);
        });

        // Listen for direction changes from others
        socket.on("player_faced", (data) => {
            // console.log("Player faced:", data); // Can be noisy
            this.updatePlayerDirection(data.id, data.direction);
        });

        // Listen for dynamic fish updates
        socket.on("fish_spawned", (fishData) => {
            console.log("Fish spawned:", fishData);
            this.addFish(fishData);
        });

        socket.on("fish_removed", (data) => {
            console.log("Fish removed:", data);
            if (data && data.id) {
                this.removeFish(data.id);
            } else {
                console.warn("Received fish_removed event without ID:", data);
            }
        });

        // Listen for cast results
        socket.on("line_casted", (data) => {
            console.log("Line casted:", data);
            this.drawCastLine(data.playerId, data.startPos, data.endPos);
        });

        socket.on("line_removed", (data) => {
            console.log("Line removed:", data);
            this.removeCastLine(data.playerId);
        });

        socket.on("cast_failed", (data) => {
            console.warn("Cast failed:", data.reason);
            // TODO: Show feedback to the player (e.g., text message)
        });

        socket.on("fish_hooked", (data) => {
            console.log("Fish hooked!", data);
            // TODO: Trigger minigame state
            this.removeCastLine(this.player.getData('id')); // Remove line visually
            this.hideHookAttemptMeter(); // Hide meter on hook
        });

        // Listen for hook attempt updates
        socket.on('hook_attempt_update', (data) => {
            this.updateHookAttemptMeter(data.threshold, data.roll, data.attempts_left, data.status);
        });

        // TODO: Add handlers for minigame events
    }

    update(time, delta) {
        // Update charge bar visual
        if (this.isCharging && this.chargeBar && this.chargeBarBg) {
            const maxChargeTime = 2000; // Max charge duration in ms (e.g., 2 seconds)
            const chargeDuration = time - this.chargeStartTime;
            const chargeRatio = Phaser.Math.Clamp(chargeDuration / maxChargeTime, 0, 1);
            this.chargeBar.scaleX = chargeRatio;
            // Position bar near player
            // Center the background bar
            this.chargeBarBg.x = this.player.x;
            this.chargeBarBg.y = this.player.y - 20;
            // Align the yellow bar's left edge with the background bar's left edge
            this.chargeBar.x = this.chargeBarBg.x - (this.chargeBarBg.width * 0.5); // Align left edge (since bg origin is 0.5)
            this.chargeBar.y = this.chargeBarBg.y; // Same y position
        }


        if (!this.player) return; // Don't do anything until player is initialized

        // --- Player Input ---
        this.handleMovementInput(delta); // Handles W/S movement
        this.handleDirectionInput(); // Handles A/D turning
        this.handleCancelInput(); // Handles C key press for cancellation

        // Update hook meter text position if visible
        if (this.player && this.hookMeterText && this.hookMeterText.visible) {
             this.hookMeterText.setPosition(this.player.x, this.player.y - 45); // Adjust position relative to player
        }
    }

    // --- Input Handling Methods ---

    handleCancelInput() {
        const myId = this.player ? this.player.getData('id') : null;
        if (!myId) return;

        if (Phaser.Input.Keyboard.JustDown(this.wasd.cancel)) {
            const myState = this.playerStates[myId] || 'unknown';

            if (this.isCharging) {
                console.log("Cancelling cast charge via C key.");
                this.isCharging = false;
                this.chargeStartTime = 0;
                if (this.chargeBar) this.chargeBar.setVisible(false);
                if (this.chargeBarBg) this.chargeBarBg.setVisible(false);
            } else if (myState === 'fishing') {
                console.log("Cancelling fishing attempt via C key.");
                socket.emit("cancel_cast"); // Tell server to cancel
                this.hideHookAttemptMeter(); // Hide meter immediately locally
            } else {
                 console.log("C key pressed, but not charging or fishing.");
            }
        }
    }

    // Handles forward/backward movement based on current direction using W/S keys
    handleMovementInput(delta) {
        const myId = this.player ? this.player.getData('id') : null;
        if (!myId) return;

        let moveSpeed = 0;
        const speed = 150; // pixels per second

        if (this.wasd.up.isDown) { // Move Forward (W)
            moveSpeed = speed;
        } else if (this.wasd.down.isDown) { // Move Backward (S)
            moveSpeed = -speed;
        }

        if (moveSpeed !== 0) {
            const currentDirection = this.playerDirections[myId] || 'down';
            let dx = 0;
            let dy = 0;

            // Calculate movement vector based on direction
            switch (currentDirection) {
                case 'up':    dy = -1; break;
                case 'down':  dy = 1;  break;
                case 'left':  dx = -1; break;
                case 'right': dx = 1;  break;
            }

            // Apply speed and delta time
            dx *= moveSpeed * (delta / 1000);
            dy *= moveSpeed * (delta / 1000);

            const newX = this.player.x + dx;
            const newY = this.player.y + dy;

            // Basic boundary check
            this.player.x = Phaser.Math.Clamp(newX, 0, GAME_WIDTH);
            this.player.y = Phaser.Math.Clamp(newY, 0, GAME_HEIGHT);

            // Move the local indicator immediately
             if (this.directionIndicator[myId]) {
                this.directionIndicator[myId].setPosition(this.player.x, this.player.y);
            }

            // Send position update to server (throttle this later)
            socket.emit("player_move", { x: this.player.x, y: this.player.y });
        }
    }

    // Handles turning left/right with A/D keys
    handleDirectionInput() {
        const myId = this.player ? this.player.getData('id') : null;
        if (!myId) return;

        let currentDirection = this.playerDirections[myId] || 'down';
        let newDirection = currentDirection;
        let directionChanged = false;

        // Turning logic
        if (Phaser.Input.Keyboard.JustDown(this.wasd.left)) { // Turn Left (A)
            switch (currentDirection) {
                case 'up':    newDirection = 'left'; break;
                case 'left':  newDirection = 'down'; break;
                case 'down':  newDirection = 'right'; break;
                case 'right': newDirection = 'up'; break;
            }
            directionChanged = true;
        } else if (Phaser.Input.Keyboard.JustDown(this.wasd.right)) { // Turn Right (D)
             switch (currentDirection) {
                case 'up':    newDirection = 'right'; break;
                case 'right': newDirection = 'down'; break;
                case 'down':  newDirection = 'left'; break;
                case 'left':  newDirection = 'up'; break;
            }
            directionChanged = true;
        }

        // Update and emit if direction changed
        if (directionChanged) {
            console.log(`Facing ${newDirection}`);
            this.updatePlayerDirection(myId, newDirection); // Update local visual immediately
            socket.emit("player_face", { direction: newDirection });
        }
    }

    startCharging(pointer) {
        // Only charge if player exists and is idle
        const myId = this.player ? this.player.getData('id') : null;
        const myState = myId ? this.playerStates[myId] : 'unknown';

        if (!this.player || this.isCharging || myState !== 'idle') {
             if (myState !== 'idle') console.log("Cannot charge, not idle. State:", myState);
            return;
        }
        console.log("Starting charge...");
        this.isCharging = true;
        this.chargeStartTime = this.time.now;

        // Create/show charge bar
        if (!this.chargeBarBg) {
            this.chargeBarBg = this.add.rectangle(0, 0, 50, 5, 0x000000).setOrigin(0.5); // Background
            this.chargeBar = this.add.rectangle(0, 0, 50, 5, 0xffff00).setOrigin(0, 0.5); // Yellow bar
        }
        this.chargeBarBg.setVisible(true).setDepth(1);
        this.chargeBar.setVisible(true).setDepth(2);
        this.chargeBar.scaleX = 0; // Reset scale
    }

    castLine(pointer) {
        // Check state again in case it changed during charge
        const myId = this.player ? this.player.getData('id') : null;
        const myState = myId ? this.playerStates[myId] : 'unknown';

        if (!this.isCharging || !this.player || myState !== 'idle') {
             // If state changed during charge, just cancel charge
             if (this.isCharging) {
                 console.log("Cancelling charge due to state change or missing player.");
                 this.isCharging = false;
                 if (this.chargeBar) this.chargeBar.setVisible(false);
                 if (this.chargeBarBg) this.chargeBarBg.setVisible(false);
             }
            return;
        }
        console.log("Casting line...");
        const maxChargeTime = 2000;
        const minPower = 0.1;
        const maxPower = 1.0;
        const chargeDuration = this.time.now - this.chargeStartTime;
        const chargeRatio = Phaser.Math.Clamp(chargeDuration / maxChargeTime, 0, 1);
        const castPower = minPower + (maxPower - minPower) * chargeRatio;

        const targetX = pointer.worldX;
        const targetY = pointer.worldY;

        console.log(`Emitting start_cast: power=${castPower.toFixed(2)}, target=(${targetX.toFixed(0)}, ${targetY.toFixed(0)})`);
        socket.emit("start_cast", { power: castPower, target: { x: targetX, y: targetY } });

        this.isCharging = false;
        // Hide charge bar
        if (this.chargeBar) this.chargeBar.setVisible(false);
        if (this.chargeBarBg) this.chargeBarBg.setVisible(false);
    }


    // --- Helper Functions ---

    // Renamed from initializeWorld to avoid confusion
    initializeOthers(worldData) {
        console.log("Initializing others based on world state...");
        // Clear existing *other* players and fish
        Object.values(this.otherPlayers).forEach(playerGroup => {
             playerGroup.rect.destroy();
             playerGroup.stateText.destroy();
             if (this.directionIndicator[playerGroup.rect.getData('id')]) {
                 this.directionIndicator[playerGroup.rect.getData('id')].destroy();
             }
        });
        this.otherPlayers = {};
        this.playerStates = {};
        this.playerDirections = {};
        this.directionIndicator = {}; // Clear indicators too

        Object.values(this.fishes).forEach(rect => rect.destroy());
        this.fishes = {};
        // DO NOT destroy self.player here, it's initialized by 'welcome'

        // Add other players from the world state
        worldData.players.forEach(playerData => {
            // Ensure we don't add ourselves if the server accidentally included us
            // Check if this.player exists and has data before comparing IDs
            if (!this.player || !this.player.getData('id') || playerData.id !== this.player.getData('id')) {
                 this.addOtherPlayer(playerData);
            } else {
                 console.log(`Skipping adding self (${playerData.id}) from world_state.`);
            }
        });

        // Add fish
        worldData.fish.forEach(fishData => {
            this.addFish(fishData);
        });
    }

    // Called when the server confirms our join and gives us our data
    initializeSelf(playerData) {
         if (this.player) {
             this.player.destroy();
             if (this.stateText) this.stateText.destroy();
             const myId = this.player.getData('id');
             if (this.directionIndicator[myId]) {
                 this.directionIndicator[myId].destroy();
                 delete this.directionIndicator[myId];
             }
         }
         // Create a red rectangle for the player
         this.player = this.add.rectangle(playerData.position.x, playerData.position.y, 16, 16, 0xff0000); // x, y, width, height, color
         this.physics.add.existing(this.player); // Add physics body
         this.player.body.setCollideWorldBounds(true); // Keep player within game bounds
         this.player.setData('id', playerData.id); // Store ID
         console.log(`Initialized self: ${playerData.name} (${playerData.id})`);
         // Initialize self state and direction
         this.playerStates[playerData.id] = playerData.state || 'idle';
         this.playerDirections[playerData.id] = playerData.direction || 'down'; // Initialize direction
         // Add text for self state (create if it doesn't exist)
         if (!this.stateText) {
             this.stateText = this.add.text(this.player.x, this.player.y - 15, '', { fontSize: '10px', fill: '#fff', backgroundColor: '#000' }).setOrigin(0.5).setDepth(3).setVisible(false);
         }
         // Call the updated visual function with state and direction
         this.updatePlayerVisuals(playerData.id, this.playerStates[playerData.id], this.playerDirections[playerData.id]);
    } // <-- This closing brace was misplaced

    // Update player visual based on state and direction
    updatePlayerVisuals(playerId, state, direction) {
        const isSelf = this.player && this.player.getData('id') === playerId;
        const playerObj = isSelf ? this.player : (this.otherPlayers[playerId] ? this.otherPlayers[playerId].rect : null);
        const stateTextObj = isSelf ? this.stateText : (this.otherPlayers[playerId] ? this.otherPlayers[playerId].stateText : null);
        let indicator = this.directionIndicator[playerId];

        if (!playerObj) return;

        let tint = 0xffffff; // Default (white = idle)
        let stateStr = "";
        switch (state) {
            case 'fishing':
                tint = 0xffff00; // Yellow
                stateStr = "Fishing...";
                break;
            case 'hooked':
                tint = 0xffa500; // Orange
                stateStr = "Hooked!";
                break;
            case 'idle':
            default:
                tint = isSelf ? 0xff0000 : 0x0000ff; // Red for self, blue for others when idle
                stateStr = "";
                break;
        }
        playerObj.setFillStyle(tint); // Use setFillStyle for rectangles

        // Update state text
        if (stateTextObj) {
            stateTextObj.setText(stateStr).setPosition(playerObj.x, playerObj.y - 15); // Position above player
            stateTextObj.setVisible(!!stateStr); // Show only if there's text
        }

        // Update direction indicator
        if (!indicator) {
            indicator = this.add.graphics().setDepth(playerObj.depth + 1); // Draw on top
            this.directionIndicator[playerId] = indicator;
        }
        indicator.clear();
        indicator.lineStyle(2, 0x000000, 1); // Black line
        indicator.setPosition(playerObj.x, playerObj.y);

        const indicatorLength = 8; // Length of the direction line
        switch (direction) {
            case 'up':    indicator.moveTo(0, 0).lineTo(0, -indicatorLength); break;
            case 'down':  indicator.moveTo(0, 0).lineTo(0, indicatorLength); break;
            case 'left':  indicator.moveTo(0, 0).lineTo(-indicatorLength, 0); break;
            case 'right': indicator.moveTo(0, 0).lineTo(indicatorLength, 0); break;
            default: // Default to down if direction is unknown
                 indicator.moveTo(0, 0).lineTo(0, indicatorLength); break;
        }
        indicator.strokePath();
    }

     updatePlayerState(playerId, newState) {
        this.playerStates[playerId] = newState;
        // Use existing direction when updating state
        this.updatePlayerVisuals(playerId, newState, this.playerDirections[playerId] || 'down');
    }

    updatePlayerDirection(playerId, newDirection) {
        this.playerDirections[playerId] = newDirection;
        // Use existing state when updating direction
        this.updatePlayerVisuals(playerId, this.playerStates[playerId] || 'idle', newDirection);
    }


    addOtherPlayer(playerData) {
        if (this.otherPlayers[playerData.id]) return; // Already exists

        // Create a blue rectangle for other players
        const otherPlayerRect = this.add.rectangle(playerData.position.x, playerData.position.y, 16, 16, 0x0000ff);
        otherPlayerRect.setData('id', playerData.id);
        // Add text object for state display
        const stateText = this.add.text(playerData.position.x, playerData.position.y - 15, '', { fontSize: '10px', fill: '#fff', backgroundColor: '#000' }).setOrigin(0.5).setDepth(3).setVisible(false);

        this.otherPlayers[playerData.id] = { rect: otherPlayerRect, stateText: stateText }; // Indicator added in updatePlayerVisuals
        this.playerStates[playerData.id] = playerData.state || 'idle'; // Store initial state
        this.playerDirections[playerData.id] = playerData.direction || 'down'; // Store initial direction
        this.updatePlayerVisuals(playerData.id, this.playerStates[playerData.id], this.playerDirections[playerData.id]); // Apply initial visual

        console.log(`Added other player: ${playerData.name} (${playerData.id}) state: ${this.playerStates[playerData.id]}`);
    }

    removeOtherPlayer(playerId) {
        const playerGroup = this.otherPlayers[playerId];
        if (playerGroup) {
            playerGroup.rect.destroy();
            playerGroup.stateText.destroy();
            // Remove direction indicator if it exists
            if (this.directionIndicator[playerId]) {
                this.directionIndicator[playerId].destroy();
                delete this.directionIndicator[playerId];
            }
            delete this.otherPlayers[playerId];
            delete this.playerStates[playerId]; // Clean up state
            delete this.playerDirections[playerId]; // Clean up direction
            console.log(`Removed other player: ${playerId}`);
        }
    }

    updateOtherPlayerPosition(playerData) {
        const playerGroup = this.otherPlayers[playerData.id];
        if (playerGroup) {
            // Could add tweening later for smoother movement
            playerGroup.rect.setPosition(playerData.position.x, playerData.position.y);
            playerGroup.stateText.setPosition(playerData.position.x, playerData.position.y - 15); // Move text too
            // Move direction indicator too
            if (this.directionIndicator[playerData.id]) {
                this.directionIndicator[playerData.id].setPosition(playerData.position.x, playerData.position.y);
            }
        } else {
            // Player might have joined just now, add them
            this.addOtherPlayer(playerData);
        }
    }

    // --- Meter and Visual Helpers ---

    createHookAttemptMeter() {
        // Create graphics only once
        if (!this.hookMeterBg) {
            const meterWidth = 100;
            const meterHeight = 8;
            const meterYOffset = -35; // Position above player, below charge bar

            this.hookMeterBg = this.add.rectangle(0, 0, meterWidth, meterHeight, 0x555555).setOrigin(0.5); // Grey background
            this.hookMeterRoll = this.add.rectangle(0, 0, meterWidth, meterHeight, 0xff0000).setOrigin(0, 0.5); // Red bar for roll
            this.hookMeterThreshold = this.add.rectangle(0, 0, 2, meterHeight + 2, 0x00ff00).setOrigin(0.5); // Green line for threshold
            this.hookMeterText = this.add.text(0, 0, '', { fontSize: '10px', fill: '#fff' }).setOrigin(0.5);

            // Initially hidden
            this.hookMeterBg.setVisible(false).setDepth(1);
            this.hookMeterRoll.setVisible(false).setDepth(2);
            this.hookMeterThreshold.setVisible(false).setDepth(3);
            this.hookMeterText.setVisible(false).setDepth(3);
        }
    }

    updateHookAttemptMeter(threshold, roll, attempts_left, status) {
        this.createHookAttemptMeter(); // Ensure graphics exist

        if (!this.player) return; // Need player position

        // Position the meter elements relative to the player
        const meterX = this.player.x;
        const meterY = this.player.y - 35; // Position above player
        const meterWidth = this.hookMeterBg.width;

        this.hookMeterBg.setPosition(meterX, meterY).setVisible(true);
        this.hookMeterRoll.setPosition(meterX - meterWidth * 0.5, meterY).setVisible(true);
        this.hookMeterThreshold.setPosition(meterX - meterWidth * 0.5 + meterWidth * threshold, meterY).setVisible(true);
        this.hookMeterText.setPosition(meterX, meterY - 10).setVisible(true); // Text above meter

        if (status === 'no_fish_nearby') {
            this.hookMeterRoll.scaleX = 0;
            this.hookMeterThreshold.setVisible(false); // Hide threshold if no fish
            this.hookMeterText.setText(`No Fish Nearby (${attempts_left})`);
        } else {
            this.hookMeterRoll.scaleX = Phaser.Math.Clamp(roll, 0, 1);
            // Color roll bar based on success/fail for this specific roll
            this.hookMeterRoll.setFillStyle(roll < threshold ? 0x00ff00 : 0xff0000); // Green if under threshold, red otherwise
            this.hookMeterThreshold.setVisible(true);
            this.hookMeterText.setText(`Roll: ${roll.toFixed(2)} / Thr: ${threshold.toFixed(2)} (${attempts_left})`);
        }
    }

    hideHookAttemptMeter() {
         if (this.hookMeterBg) this.hookMeterBg.setVisible(false);
         if (this.hookMeterRoll) this.hookMeterRoll.setVisible(false);
         if (this.hookMeterThreshold) this.hookMeterThreshold.setVisible(false);
         if (this.hookMeterText) this.hookMeterText.setVisible(false);
    }


    // --- Game Object Handling ---

    drawCastLine(playerId, startPos, endPos) {
        // Remove existing line for this player first
        this.removeCastLine(playerId);

        const line = this.add.graphics();
        line.lineStyle(1, 0xffffff, 0.8); // White line, 1px thick, 80% alpha
        line.moveTo(startPos.x, startPos.y);
        line.lineTo(endPos.x, endPos.y);
        line.strokePath();
        line.setData('playerId', playerId); // Associate line with player
        this.lines[playerId] = line;
    }

    removeCastLine(playerId) {
        const line = this.lines[playerId];
        if (line) {
            line.destroy();
            delete this.lines[playerId];
        }
        // Hide meter if we were fishing and line is removed (e.g., timeout, cancel)
        if (this.player && this.player.getData('id') === playerId) {
            this.hideHookAttemptMeter();
        }
    }

    addFish(fishData) {
         if (this.fishes[fishData.id]) return; // Already exists

        // Create a green rectangle for fish
        const fishRect = this.add.rectangle(fishData.position.x, fishData.position.y, 10, 5, 0x00ff00); // Make fish smaller
        fishRect.setData('id', fishData.id);
        // Maybe change color based on rarity?
        // if (fishData.rarity === 'Rare') fishRect.setFillStyle(0xffff00);
        this.fishes[fishData.id] = fishRect;
    }

    removeFish(fishId) {
         const fishRect = this.fishes[fishId];
        if (fishRect) {
            fishRect.destroy();
            delete this.fishes[fishId];
        }
    }
}


// --- Phaser Game Configuration ---
const config = {
    type: Phaser.AUTO, // Use WebGL if available, otherwise Canvas
    width: GAME_WIDTH,
    height: GAME_HEIGHT,
    physics: {
        default: 'arcade', // Simple physics engine
        arcade: {
            // gravity: { y: 0 }, // No gravity needed for top-down
            debug: false // Set to true to see physics bodies
        }
    },
    scene: [MainScene] // Add more scenes later if needed
};

// --- Initialize Game ---
const game = new Phaser.Game(config);

console.log("Phaser game initialized.");
