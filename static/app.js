<script>
new Vue({
    el: '#app',
    data: {
        agent: null,
        goal: '',
        selectedBackend: 'openai',
        nextAction: null,
        completionStatus: null,
        conclusion: null,
        feedback: '',
        decision: null,
        showAdjustForm: false,
        adjustmentInput: '',
        planCompleted: false,
        isAllowingAll: false,
        projectFiles: []
    },
    computed: {
        allActionsCompleted() {
            return this.planCompleted;
        },
        isAllowAllDisabled() {
            return this.isAllowingAll || this.planCompleted;
        }
    },
    methods: {
        createAgent() {
            axios.post('/create_agent', { goal: this.goal, backend: this.selectedBackend })
                .then(response => {
                    this.agent = response.data;
                    this.nextAction = this.agent.next_action;
                    this.refreshProjectFiles();
                })
                .catch(error => {
                    console.error('Error creating agent:', error);
                    alert('An error occurred while creating the agent. Please try again.');
                });
        },
        executeAction(allowed) {
            return axios.post('/execute_action', { action: this.nextAction, allowed: allowed })
                .then(response => {
                    this.agent = response.data.agent;
                    this.nextAction = response.data.next_action;
                    this.completionStatus = response.data.completion_status;
                    this.planCompleted = response.data.plan_completed;
                    this.refreshProjectFiles();
                    this.$nextTick(() => {
                        this.scrollMemoryToBottom();
                    });
                })
                .catch(error => {
                    console.error('Error executing action:', error);
                    this.isAllowingAll = false;
                });
        },
        allowAll() {
            this.isAllowingAll = true;
            this.executeAllActions();
        },
        executeAllActions() {
            if (this.nextAction && this.nextAction.type !== 'plan_completed') {
                this.executeAction(true).then(() => {
                    this.$nextTick(() => {
                        this.executeAllActions();
                    });
                });
            } else {
                this.isAllowingAll = false;
                this.generateConclusion();
            }
        },
        generateConclusion() {
            axios.get('/generate_conclusion')
                .then(response => {
                    this.conclusion = response.data.conclusion;
                })
                .catch(error => {
                    console.error('Error generating conclusion:', error);
                });
        },
        submitFeedback() {
            axios.post('/process_feedback', { feedback: this.feedback })
                .then(response => {
                    this.decision = response.data.decision;
                    this.agent = response.data.agent;
                    this.feedback = '';
                })
                .catch(error => {
                    console.error('Error submitting feedback:', error);
                });
        },
        adjustAction() {
            axios.post('/adjust_action', { user_input: this.adjustmentInput })
                .then(response => {
                    this.nextAction = response.data.updated_action;
                    this.agent = response.data.agent;
                    this.showAdjustForm = false;
                    this.adjustmentInput = '';
                })
                .catch(error => {
                    console.error('Error adjusting action:', error);
                });
        },
        scrollMemoryToBottom() {
            const memorySection = this.$refs.memorySection;
            if (memorySection) {
                memorySection.scrollTop = memorySection.scrollHeight;
            }
        },
        refreshProjectFiles() {
            axios.get('/get_project_files')
                .then(response => {
                    this.projectFiles = response.data.project_files;
                })
                .catch(error => {
                    console.error('Error refreshing project files:', error);
                });
        }
    },
    updated() {
        this.scrollMemoryToBottom();
    }
});
</script>