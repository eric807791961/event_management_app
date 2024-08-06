'use client'

import { useState, useEffect } from 'react'
import axios from 'axios'

interface Event {
  id: number
  link: string
  event_name: string
  event_date: string
  event_time: string
  event_location: string
  image_url: string
}

export default function Home() {
  const [events, setEvents] = useState<Event[]>([])

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const response = await axios.get('http://localhost:5000/api/events')
        setEvents(response.data)
      } catch (error) {
        console.error('Error fetching events:', error)
      }
    }

    fetchEvents()
  }, [])

  return (
    <main className="p-4">
      <h1 className="text-2xl font-bold mb-4">Events</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {events.map((event) => (
          <div key={event.id} className="border p-4 rounded-lg">
            <img src={event.image_url} alt={event.event_name} className="w-full h-48 object-cover mb-2" />
            <h2 className="text-xl font-semibold">{event.event_name}</h2>
            <p>Date: {event.event_date}</p>
            <p>Time: {event.event_time}</p>
            <p>Location: {event.event_location}</p>
            <a href={event.link} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline">
              More Info
            </a>
          </div>
        ))}
      </div>
    </main>
  )
}