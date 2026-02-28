import React, { useState } from 'react'
import { cn } from '@/lib/utils'

const sizeStyles = {
  sm: 'h-8 w-8 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-14 w-14 text-lg',
} as const

export type AvatarSize = keyof typeof sizeStyles

export interface AvatarProps {
  src?: string
  name: string
  size?: AvatarSize
  className?: string
}

export const Avatar: React.FC<AvatarProps> = ({
  src,
  name,
  size = 'md',
  className,
}) => {
  const [imgError, setImgError] = useState(false)
  const initial = name.charAt(0).toUpperCase()

  const showFallback = !src || imgError

  return (
    <div
      className={cn(
        'relative shrink-0 overflow-hidden rounded-full',
        sizeStyles[size],
        showFallback && 'flex items-center justify-center bg-accent font-semibold text-white',
        className,
      )}
    >
      {!showFallback ? (
        <img
          src={src}
          alt={name}
          onError={() => setImgError(true)}
          className="h-full w-full object-cover"
        />
      ) : (
        <span>{initial}</span>
      )}
    </div>
  )
}

Avatar.displayName = 'Avatar'

export default Avatar
