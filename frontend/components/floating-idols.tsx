"use client"

import { motion } from "framer-motion"

const idolImages = [
  "/idols/idol1.png",
  "/idols/idol2.png",
  "/idols/idol3.png",
]

const positions = [
  { top: "23%", left: "20%", width: 120, delay: 0 },
  { top: "16%", right: "9%", width: 135, delay: 0.4 },
  { bottom: "13%", left: "12%", width: 125, delay: 0.8 },
]

export function FloatingIdols() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {idolImages.map((src, index) => {
        const pos = positions[index]

        return (
          <motion.div
            key={src}
            className="absolute drop-shadow-2xl"
            style={{
              width: pos.width,
              ...pos,
            }}
            initial={{ opacity: 0, scale: 0.7, y: 20 }}
            animate={{
              opacity: 0.9,
              scale: 1,
              y: [0, -14, 0],
              rotate: [-4, 4, -4],
            }}
            transition={{
              opacity: { duration: 0.8, delay: pos.delay },
              scale: { duration: 0.8, delay: pos.delay },
              y: {
                duration: 3 + index * 0.4,
                repeat: Infinity,
                ease: "easeInOut",
                delay: pos.delay,
              },
              rotate: {
                duration: 4 + index * 0.3,
                repeat: Infinity,
                ease: "easeInOut",
              },
            }}
          >
            <img
              src={src}
              alt=""
              className="h-auto w-full object-contain"
            />
          </motion.div>
        )
      })}
    </div>
  )
}