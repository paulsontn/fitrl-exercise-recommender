"""
SYSTEM ARCHITECTURE & DATA FLOW
"""

# ============================================================================
# SYSTEM ARCHITECTURE
# ============================================================================

┌─────────────────────────────────────────────────────────────────────────┐
│                   RL-BASED EXERCISE RECOMMENDATION SYSTEM               │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                            CLIENT INTERFACES                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────┐ │
│  │   Python Script      │  │   REST API Client    │  │   Web Portal │ │
│  │   (Direct Import)    │  │   (HTTP Requests)    │  │  (Future)    │ │
│  └──────────────────────┘  └──────────────────────┘  └──────────────┘ │
│           │                        │                        │           │
└───────────┼────────────────────────┼────────────────────────┼───────────┘
            │                        │                        │
            │                        │                        │
            └─────────────┬──────────┴────────────────────────┘
                          │
            ┌─────────────▼────────────────────┐
            │   API SERVER (Flask)             │
            │   ┌──────────────────────────┐   │
            │   │ Endpoints                │   │
            │   │ - /register              │   │
            │   │ - /recommendations       │   │
            │   │ - /workout               │   │
            │   │ - /feedback              │   │
            │   │ - /exercises             │   │
            │   │ - /user/<id>             │   │
            │   └──────────────────────────┘   │
            └──────────────┬────────────────────┘
                           │
            ┌──────────────▼──────────────────┐
            │   RECOMMENDATION ENGINE         │
            │   ┌──────────────────────────┐  │
            │   │ RecommendationSystem     │  │
            │   │ - register_user()        │  │
            │   │ - get_recommender()      │  │
            │   │ - get_user_profile()     │  │
            │   └──────────────────────────┘  │
            │   ┌──────────────────────────┐  │
            │   │ ExerciseRecommender      │  │
            │   │ - get_recommendations()  │  │
            │   │ - get_workout_plan()     │  │
            │   │ - provide_feedback()     │  │
            │   └──────────────────────────┘  │
            └──────────┬───────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
    ┌───▼──┐     ┌────▼────┐   ┌────▼──────┐
    │ RL   │     │Exercise  │   │User       │
    │Agent │     │Database  │   │Profile    │
    │─────│     │─────────│   │Manager    │
    │DQN  │     │15+      │   │──────────│
    │    │     │Exer     │   │Create    │
    │Policy │   │cises    │   │Update    │
    │Grad  │   │Filter   │   │Track     │
    │      │   │by:      │   │Goals     │
    │      │   │-Level   │   │Injuries  │
    │      │   │-Muscle  │   │Equipment │
    │      │   │-Suit    │   │Prefs     │
    │      │   │ for     │   │         │
    │      │   │User     │   │         │
    └──┬───┘   └────┬────┘   └────┬────┘
       │            │             │
       │      ┌─────▼─────┐       │
       │      │Exercise   │       │
       │      │Recommendation    │
       │      │Environment       │
       │      │(Gym-compatible)  │
       │      │─────────────────│
       │      │State:15-D vector│
       │      │Actions:Exercise │
       │      │Rewards:Feedback │
       │      │Punishments:     │
       │      │Injuries         │
       │      └─────┬───────────┘
       │            │
       └────────┬───┘
                │
        ┌───────▼─────────┐
        │ Training Loop   │
        │(main.py,trainer)│
        │───────────────│
        │-100 episodes   │
        │-Experience     │
        │ replay         │
        │-Target network │
        │ updates        │
        │-Save weights   │
        └────────────────┘

# ============================================================================
# DATA FLOW: GETTING A RECOMMENDATION
# ============================================================================

USER REQUEST
     │
     ▼
┌─────────────────────────────────────────┐
│ 1. API Receives Request                 │
│    POST /api/recommendations/user_001   │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 2. Retrieve User Profile                │
│    - age, fitness_level, goals          │
│    - injuries, equipment, preferences   │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 3. Get Suitable Exercises               │
│    Filter by:                           │
│    - No injury contraindications        │
│    - Have required equipment            │
│    - Match fitness level                │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 4. Create User State Vector             │
│    [age, fitness, time, goals,          │
│     exercise_history, feedback_scores]  │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 5. Compute Q-Values                     │
│    DQN forward pass through network     │
│    output[i] = Q-value for action i     │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 6. Select Top-K Exercises               │
│    Sort by Q-values                     │
│    Return top 5 (or requested number)   │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 7. Generate Rationale                   │
│    For each exercise:                   │
│    - Goal alignment score               │
│    - Preferred exercise indicator       │
│    - Difficulty match                   │
│    - Time fit                           │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 8. Return Response                      │
│    [                                    │
│      {exercise_id, name, intensity,     │
│       duration, rationale, ...},        │
│      ...                                │
│    ]                                    │
└────────────────┬────────────────────────┘
                 │
                 ▼
            RESPONSE TO USER

# ============================================================================
# DATA FLOW: TRAINING THE AGENT
# ============================================================================

TRAINING INITIATION
     │
     ▼
┌─────────────────────────────────────┐
│ 1. Create Environment               │
│    - User profile                   │
│    - Suitable exercises             │
└────────────────┬────────────────────┘
                 │
     ┌───────────┼───────────┐
     │ FOR EACH EPISODE      │
     │ (100 times)           │
     ▼                       │
┌─────────────────────────────────────┐
│ 2. Reset Environment                │
│    - Clear history                  │
│    - Get initial state              │
└────────────────┬────────────────────┘
                 │
     ┌───────────┼───────────┐
     │ FOR EACH STEP         │
     │ (up to 30 per episode)│
     ▼                       │
┌─────────────────────────────────────┐
│ 3. Agent Selects Action             │
│    - Epsilon-greedy                 │
│    - Explore vs Exploit             │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ 4. Environment Simulates Feedback   │
│    - Calculate user satisfaction    │
│    - Based on exercise properties   │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ 5. Compute Reward                   │
│    - User satisfaction (main)       │
│    - Goal alignment bonus           │
│    - Variety incentive              │
│    - Penalty for repetition         │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ 6. Store Experience                 │
│    (state, action, reward,          │
│     next_state, done) → memory      │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ 7. Train on Mini-Batch              │
│    - Sample 32 experiences          │
│    - Forward pass (current network) │
│    - Compute target values          │
│    - MSE loss                       │
│    - Backpropagation                │
│    - Gradient descent update        │
└────────────────┬────────────────────┘
                 │
                 └──────────┬──────────┐
                            │          │ (continue steps 3-7)
                            │          └──────┐
                            │                 │
     ┌──────────────────────┼─────────────────┘
     │ (update target network every 4 episodes)
     ▼
┌─────────────────────────────────────┐
│ 8. Update Target Network            │
│    Copy weights from main network   │
└────────────────┬────────────────────┘
                 │
                 │ (repeat for 100 episodes)
                 └──────────────────────┐
                                        │
                                        ▼
                           ┌────────────────────┐
                           │ Save Trained Agent │
                           │ trained_agent.pt   │
                           └────────────────────┘

# ============================================================================
# DATA FLOW: USER FEEDBACK INTEGRATION
# ============================================================================

USER PROVIDES FEEDBACK
     │
     ▼
┌─────────────────────────────────────┐
│ 1. POST /api/feedback/<user_id>     │
│    - exercise_id                    │
│    - satisfaction_score (0-10)      │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ 2. Validate Input                   │
│    - User exists                    │
│    - Score in range [0,10]          │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ 3. Store Feedback                   │
│    user_feedback[exercise_id] =     │
│      satisfaction_score             │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ 4. Update User State                │
│    Next recommendations will        │
│    consider this feedback           │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│ 5. Bias Q-Values                    │
│    (Optional: retrain on feedback)  │
│    Agent learns from real user      │
│    behavior                         │
└────────────────┬────────────────────┘
                 │
                 ▼
            ACKNOWLEDGE RESPONSE

# ============================================================================
# COMPONENT INTERACTION DIAGRAM
# ============================================================================

┌──────────────────┐
│  API Request     │
└────────┬─────────┘
         │
         ▼
    ┌────────────┐
    │   Flask    │──────────┐
    │   Router   │          │
    └────────────┘          │
         │                  │
    ┌────▼──────────────────▼───────────┐
    │  Recommendation System            │
    │  ┌────────────────────────────┐   │
    │  │ RecommendationSystem       │   │
    │  │                            │   │
    │  │  ┌──────────────────────┐  │   │
    │  │  │ Exercise Recommender │  │   │
    │  │  │ (Per User)          │  │   │
    │  │  └──────────────────────┘  │   │
    │  └────────────────────────────┘   │
    │           │     │         │        │
    │           │     │         │        │
    │      ┌────▼─┐   │      ┌──▼────┐   │
    │      │ RL   │───│      │User   │   │
    │      │Agent │   │      │Profile│   │
    │      │ DQN  │   │      │Manager│   │
    │      └────┬─┘   │      └──┬────┘   │
    │           │     │         │        │
    │           │  ┌──▼────────▼──┐     │
    │           │  │ Exercise     │     │
    │           │  │ Database     │     │
    │           │  └──────────────┘     │
    │           │                       │
    │      ┌────▼──────────────────┐    │
    │      │ Exercise Environment  │    │
    │      │ (Gym-compatible)      │    │
    │      │                       │    │
    │      │ - State: User Vector  │    │
    │      │ - Action: Exercise ID │    │
    │      │ - Reward: Feedback    │    │
    │      │ - Constraints:        │    │
    │      │   Injuries, Equipment │    │
    │      └───────────────────────┘    │
    └──────────────────────────────────┘
         │
         ▼
    ┌──────────────┐
    │  Response    │
    │  JSON        │
    └──────────────┘

# ============================================================================
# STATE SPACE REPRESENTATION
# ============================================================================

STATE VECTOR (15-dimensional):
┌─────────────────────────────────────────────┐
│ Index │ Feature                 │ Normalization  │
├─────────────────────────────────────────────┤
│  0    │ Age                     │ / 100         │
│  1    │ Fitness Level (1-3)     │ / 3           │
│  2    │ Available Time (min)    │ / 120         │
│  3    │ Number of Goals (0-5)   │ / 5           │
│  4-8  │ Recent Exercise Indices │ / max_exercises
│  9-13 │ Recent Satisfaction     │ / 10          │
│  14   │ Consistency Streak      │ / 20          │
└─────────────────────────────────────────────┘

Example: User Profile
┌─────────────────────────────────────────────┐
│ Age: 30 (normalized: 0.30)                  │
│ Fitness Level: INTERMEDIATE (normalized: 0.67) │
│ Available Time: 45 min (normalized: 0.375)  │
│ Goals: 2 (normalized: 0.40)                 │
│ Recent exercises: [5, 7, 3, 9, 12]          │
│ Satisfaction scores: [7.5, 8.2, 6.9, 7.8, 8.1] │
│ Streak: 5 sessions (normalized: 0.25)       │
│                                              │
│ STATE VECTOR:                               │
│ [0.30, 0.67, 0.375, 0.40, 0.25, 0.35, 0.15,│
│  0.45, 0.60, 0.75, 0.82, 0.69, 0.78, 0.81, │
│  0.25]                                      │
└─────────────────────────────────────────────┘

# ============================================================================
# ACTION SPACE REPRESENTATION
# ============================================================================

ACTION SPACE: Discrete (Suitable Exercises)
┌────────────────────────────────────────┐
│ Action Index │ Exercise       │ Details │
├────────────────────────────────────────┤
│      0       │ Walking        │ ●●●●●○  │
│      1       │ Jogging        │ ●●●●●●  │
│      2       │ Push-ups       │ ●●●●○○  │
│      3       │ Bench Press    │ ●●●●●●● │
│      4       │ Squats         │ ●●●●●●  │
│      5       │ Planks         │ ●●●○○○  │
│     ...      │  ...           │  ...    │
└────────────────────────────────────────┘

Note: Available actions vary per user based on:
- Fitness level
- Injuries (filtered out)
- Equipment availability
- Time constraints

# ============================================================================
# REWARD FUNCTION BREAKDOWN
# ============================================================================

Total Reward = R_satisfaction + R_goals + R_variety - R_penalty

R_satisfaction:  User feedback score (0-10)
                 [Primary reward signal]

R_goals:         + 1.0 per goal aligned with selected exercise
                 Examples:
                 - Muscle gain: intensity >= 5
                 - Weight loss: intensity >= 6, calories >= 5
                 - Flexibility: yoga or stretching

R_variety:       + 0.1 × unique_exercise_count
                 Capped at 2.0
                 Encourages trying new exercises

R_penalty:       - 0.5 × max(0, repeat_count - 3)
                 Prevents excessive repetition
                 Encourages diversity

# ============================================================================
