#include "WarCraftingStation.h"
#include "Net/UnrealNetwork.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Pawn.h"

AWarCraftingStation::AWarCraftingStation() { bReplicates = true; }

void AWarCraftingStation::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AWarCraftingStation, StationKind);
    DOREPLIFETIME(AWarCraftingStation, InteractionRadius);
}

bool AWarCraftingStation::CanInteract(const APawn* Pawn) const
{
    const UStaticMesh* Mesh = GetStaticMeshComponent()->GetStaticMesh();
    return Pawn && Pawn->GetWorld() == GetWorld() && !IsActorBeingDestroyed() && Mesh
        && Mesh->GetPathName().StartsWith(TEXT("/Game/Imported/")) && !IsHidden()
        && GetStaticMeshComponent()->IsVisible() && !Pawn->IsActorBeingDestroyed()
        && FMath::IsFinite(InteractionRadius) && InteractionRadius > 0.f
        && FVector::DistSquared(Pawn->GetActorLocation(), GetActorLocation()) <= FMath::Square(InteractionRadius);
}
