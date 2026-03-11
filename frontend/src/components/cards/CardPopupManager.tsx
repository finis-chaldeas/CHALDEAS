import { useCardPopup } from './useCardPopup'
import type { CardType } from './useCardPopup'
import CardContainer from './CardContainer'
import EventCard from './EventCard'
import PersonCard from './PersonCard'
import LocationCard from './LocationCard'
import ServantCard from './ServantCard'
import ShiftCard from './ShiftCard'

interface CardPopupManagerProps {
  onViewDetail?: (type: CardType, entityId: number) => void
}

export default function CardPopupManager({ onViewDetail }: CardPopupManagerProps) {
  const { isOpen, type, entityId, mode, position, expandCard, closeCard } = useCardPopup()

  if (!isOpen || !type || entityId == null) return null

  const handleViewDetail = onViewDetail
    ? () => { closeCard(); onViewDetail(type, entityId) }
    : undefined

  const cardContent = (() => {
    switch (type) {
      case 'event':
        return <EventCard entityId={entityId} mode={mode} onViewDetail={handleViewDetail} />
      case 'person':
        return <PersonCard entityId={entityId} mode={mode} onViewDetail={handleViewDetail} />
      case 'location':
        return <LocationCard entityId={entityId} mode={mode} onViewDetail={handleViewDetail} />
      case 'servant':
        return <ServantCard entityId={entityId} mode={mode} onViewDetail={handleViewDetail} />
      case 'shift':
        return <ShiftCard entityId={entityId} mode={mode} onViewDetail={handleViewDetail} />
      default:
        return null
    }
  })()

  return (
    <CardContainer
      type={type}
      mode={mode}
      position={position}
      onClose={closeCard}
      onExpand={mode === 'compact' ? expandCard : undefined}
    >
      {cardContent}
    </CardContainer>
  )
}
