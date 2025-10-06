<template>
  <div>
    <h1 class="text-h4 font-weight-bold mb-4">Provide Feedback</h1>
    <p class="mb-6">We appreciate you taking the time to help us improve our events.</p>
    
    <v-card>
      <v-card-text>
        <h2 class="text-h6 mb-2">Overall Satisfaction</h2>
        <v-rating
          hover
          :length="5"
          :size="48"
          active-color="yellow-accent-4"
          color="grey-lighten-1"
          class="mb-4"
        ></v-rating>

        <h2 class="text-h6 mb-2">Comments</h2>
        <v-textarea
          label="What did you like or dislike? Any suggestions for the future?"
          variant="outlined"
          rows="5"
          no-resize
        ></v-textarea>
        
        <v-btn color="primary" size="large" class="mt-4">
          Submit Feedback
        </v-btn>
      </v-card-text>
    </v-card>
  </div>
</template>