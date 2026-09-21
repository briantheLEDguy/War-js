#include "WarCraftingStation.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Pawn.h"

AWarCraftingStation::AWarCraftingStation() { bReplicates = true; }

bool AWarCraftingStation::CanInteract(const APawn* Pawn) const
{
    const UStaticMesh* Mesh = GetStaticMeshComponent()->GetStaticMesh();
    return Pawn && Pawn->GetWorld() == GetWorld() && !IsActorBeingDestroyed() && Mesh
        && Mesh->GetPathName().StartsWith(TEXT("/Game/Imported/")) && !IsHidden()
        && FMath::IsFinite(InteractionRadius) && InteractionRadius > 0.f
        && FVector::DistSquared(Pawn->GetActorLocation(), GetActorLocation()) <= FMath::Square(InteractionRadius);
}
