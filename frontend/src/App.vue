<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const center = { lat: 38.2924, lon: 27.1570 }
const rangeKm = ref(60)
const planes = ref([])
const updatedAt = ref(null)
const selected = ref(null)
const error = ref('')
let timer

const project = (plane) => {
  const xKm = (plane.lon - center.lon) * 87.5
  const yKm = (plane.lat - center.lat) * 111
  return {
    left: 50 + (xKm / rangeKm.value) * 50,
    top: 50 - (yKm / rangeKm.value) * 50,
  }
}

const visiblePlanes = computed(() =>
  planes.value.filter((plane) => {
    if (typeof plane.lat !== 'number' || typeof plane.lon !== 'number') return false
    const position = project(plane)
    return position.left >= 0 && position.left <= 100 && position.top >= 0 && position.top <= 100
  }),
)

const nearest = computed(() =>
  [...planes.value]
    .filter((plane) => plane.distance_km != null)
    .sort((a, b) => a.distance_km - b.distance_km)[0] || null,
)

const updateAge = computed(() => {
  if (!updatedAt.value) return 'veri bekleniyor'
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(updatedAt.value).getTime()) / 1000))
  return seconds < 5 ? 'şimdi' : seconds < 60 ? `${seconds} sn önce` : `${Math.floor(seconds / 60)} dk önce`
})

async function refresh() {
  try {
    const response = await fetch('/api/planes', { cache: 'no-store' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    planes.value = data.planes || []
    updatedAt.value = data.updated_at
    error.value = ''
    if (selected.value) {
      selected.value = planes.value.find((plane) => plane.icao24 === selected.value.icao24) || null
    }
  } catch (reason) {
    error.value = 'Canlı veri alınamadı'
  }
}

function toggleFullscreen() {
  if (!document.fullscreenElement) document.documentElement.requestFullscreen()
  else document.exitFullscreen()
}

onMounted(() => {
  refresh()
  timer = window.setInterval(refresh, 5000)
})

onUnmounted(() => window.clearInterval(timer))
</script>

<template>
  <main class="shell">
    <header class="topbar">
      <div>
        <span class="kicker">LTBJ · ADB TOWER</span>
        <h1>AirRadar Pro</h1>
      </div>
      <div class="actions">
        <button @click="rangeKm = rangeKm === 60 ? 30 : 60">RNG {{ rangeKm }}</button>
        <button @click="toggleFullscreen">FULL</button>
        <span class="live"><i></i> LIVE</span>
      </div>
    </header>

    <section class="layout">
      <aside class="rail">
        <article class="card">
          <span class="label">RADAR STATUS</span>
          <dl class="stats">
            <div><dt>İstasyon</dt><dd>LTBJ / ADB</dd></div>
            <div><dt>Menzil</dt><dd>{{ rangeKm }} km</dd></div>
            <div><dt>Toplam</dt><dd>{{ planes.length }}</dd></div>
            <div><dt>Görünür</dt><dd>{{ visiblePlanes.length }}</dd></div>
            <div><dt>Güncelleme</dt><dd>{{ updateAge }}</dd></div>
          </dl>
        </article>

        <article class="card nearest">
          <span class="label">EN YAKIN TRAFİK</span>
          <template v-if="nearest">
            <h2>{{ nearest.callsign }}</h2>
            <p class="route">{{ nearest.origin || '---' }} <b>→</b> {{ nearest.destination || '---' }}</p>
            <div class="metrics">
              <span><small>MESAFE</small>{{ nearest.distance_km }} km</span>
              <span><small>İRTİFA</small>{{ nearest.altitude_ft ?? '-' }} ft</span>
              <span><small>HIZ</small>{{ nearest.speed_kmh ?? '-' }} km/h</span>
              <span><small>YÖN</small>{{ nearest.heading ?? '-' }}°</span>
            </div>
          </template>
          <p v-else class="muted">Trafik bekleniyor.</p>
        </article>

        <article class="card systems">
          <span class="label">SİSTEMLER</span>
          <p><i></i> HTTPS / Nginx</p>
          <p><i></i> Flask / SQLite</p>
          <p><i></i> OpenSky feed</p>
          <p><i></i> Route resolver</p>
        </article>
      </aside>

      <section class="scope-card">
        <div class="scope-head">
          <div><span class="label">PRIMARY SURVEILLANCE DISPLAY</span><strong>İZMİR TMA · LTBJ CENTER</strong></div>
          <div class="scope-meta"><span>RNG {{ rangeKm }}</span><span>REFRESH 5S</span></div>
        </div>
        <div class="scope">
          <div class="grid"></div>
          <div v-for="ring in 4" :key="ring" class="ring" :style="{ width: `${ring * 24}%` }"></div>
          <span class="bearing north">N</span><span class="bearing east">E</span>
          <span class="bearing south">S</span><span class="bearing west">W</span>
          <div class="sweep"></div>
          <div class="airport"><span class="runway"></span><b>LTBJ</b></div>

          <button
            v-for="plane in visiblePlanes"
            :key="plane.icao24"
            class="target"
            :class="{ active: selected?.icao24 === plane.icao24, ground: plane.on_ground }"
            :style="{ left: `${project(plane).left}%`, top: `${project(plane).top}%` }"
            @click="selected = plane"
          >
            <span class="aircraft" :style="{ transform: `rotate(${plane.heading || 0}deg)` }">▲</span>
            <span class="tag">
              <strong>{{ plane.callsign }}</strong>
              <small>{{ plane.origin || '---' }}→{{ plane.destination || '---' }}</small>
              <small>{{ plane.altitude_ft ?? '-' }} · {{ plane.speed_kmh ?? '-' }}</small>
            </span>
          </button>

          <p v-if="error" class="message error">{{ error }}</p>
          <p v-else-if="!planes.length" class="message">Canlı trafik bekleniyor…</p>
        </div>
      </section>

      <aside class="detail card">
        <span class="label">TRACK DETAILS</span>
        <template v-if="selected">
          <header><div><h2>{{ selected.callsign }}</h2><p>{{ selected.country }}</p></div><button @click="selected = null">×</button></header>
          <div class="routebox"><span>{{ selected.origin || 'BİLİNMİYOR' }}</span><b>→</b><span>{{ selected.destination || 'BİLİNMİYOR' }}</span></div>
          <dl class="details">
            <div><dt>ICAO24</dt><dd>{{ selected.icao24 }}</dd></div>
            <div><dt>Mesafe</dt><dd>{{ selected.distance_km ?? '-' }} km</dd></div>
            <div><dt>İrtifa</dt><dd>{{ selected.altitude_ft ?? '-' }} ft</dd></div>
            <div><dt>Hız</dt><dd>{{ selected.speed_kmh ?? '-' }} km/h</dd></div>
            <div><dt>Heading</dt><dd>{{ selected.heading ?? '-' }}°</dd></div>
            <div><dt>Dikey hız</dt><dd>{{ selected.vertical_rate_fpm ?? '-' }} fpm</dd></div>
            <div><dt>Squawk</dt><dd>{{ selected.squawk || '-' }}</dd></div>
            <div><dt>Durum</dt><dd>{{ selected.on_ground ? 'Yerde' : 'Havada' }}</dd></div>
          </dl>
        </template>
        <p v-else class="empty">Detayları görüntülemek için radar üzerindeki bir hedefi seç.</p>
      </aside>
    </section>

    <footer><span>AIRRADAR PRO · KUVAN.DEV</span><span>HOBİ AMAÇLIDIR · ATC İÇİN KULLANILMAZ</span><span>{{ updateAge }}</span></footer>
  </main>
</template>
