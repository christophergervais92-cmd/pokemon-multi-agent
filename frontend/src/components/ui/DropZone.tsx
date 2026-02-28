import React, { useState, useRef, useCallback } from 'react'
import { Upload } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface DropZoneProps {
  onDrop: (files: File[]) => void
  accept?: string
  children?: React.ReactNode
  className?: string
}

export const DropZone: React.FC<DropZoneProps> = ({
  onDrop,
  accept,
  children,
  className,
}) => {
  const [isDragActive, setIsDragActive] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const dragCounterRef = useRef(0)

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    dragCounterRef.current += 1
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragActive(true)
    }
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    dragCounterRef.current -= 1
    if (dragCounterRef.current === 0) {
      setIsDragActive(false)
    }
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragActive(false)
      dragCounterRef.current = 0

      const files = Array.from(e.dataTransfer.files)
      if (files.length > 0) {
        onDrop(files)
      }
    },
    [onDrop],
  )

  const handleClick = useCallback(() => {
    inputRef.current?.click()
  }, [])

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files ? Array.from(e.target.files) : []
      if (files.length > 0) {
        onDrop(files)
      }
      // Reset input so the same file can be selected again
      if (inputRef.current) {
        inputRef.current.value = ''
      }
    },
    [onDrop],
  )

  return (
    <div
      onClick={handleClick}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        'cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors duration-200',
        isDragActive
          ? 'border-accent bg-accent-muted'
          : 'border-border hover:border-muted-foreground',
        className,
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        onChange={handleFileChange}
        className="hidden"
        multiple
      />
      {children || (
        <div className="flex flex-col items-center gap-2 text-muted-foreground">
          <Upload className="h-10 w-10" />
          <p className="text-sm font-medium">
            Drop files here or click to upload
          </p>
          {accept && (
            <p className="text-xs text-muted">
              Accepted: {accept}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

DropZone.displayName = 'DropZone'

export default DropZone
