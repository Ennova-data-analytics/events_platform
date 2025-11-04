<template>
  <div class="video-wrapper">
    <div class="video-container">
      <iframe
        :src="embeddedUrl"
        :title="title"
        frameborder="0"
        allowfullscreen
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        loading="lazy"
      ></iframe>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  videoId: {
    type: String,
    required: true
  },
  title: {
    type: String,
    default: 'Tutorial Video'
  }
})

const extractedVideoId = computed(() => {
  const url = props.videoId

  if (url.includes('youtube.com') || url.includes('youtu.be')) {
    const youtubeMatch = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)/)
    return youtubeMatch ? youtubeMatch[1] : url
  }

  return url
})

const embeddedUrl = computed(() => {
  return `https://www.youtube.com/embed/${extractedVideoId.value}?rel=0`
})
</script>

<style scoped>
.video-wrapper {
  margin: 20px 0;
}

.video-container {
  position: relative;
  padding-bottom: 56.25%;
  height: 0;
  overflow: hidden;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.video-container iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 8px;
}
</style>
