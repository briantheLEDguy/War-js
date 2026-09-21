#include "WarResourceNode.h"
#include "WarContentSubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Character.h"
#include "Net/UnrealNetwork.h"

AWarResourceNode::AWarResourceNode() { bReplicates = true; }
void AWarResourceNode::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AWarResourceNode, ZoneId);
    DOREPLIFETIME(AWarResourceNode, NodeId);
    DOREPLIFETIME(AWarResourceNode, VisualPropId);
}

bool AWarResourceNode::ResolveInteraction(const APawn* Pawn, FWarResourceDefinition& Definition, FString& Error) const
{
    Error = TEXT("Resource node is unavailable or too far away.");
    const UStaticMesh* Mesh = GetStaticMeshComponent()->GetStaticMesh();
    const auto* Content = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarContentSubsystem>() : nullptr;
    if (!Pawn || Pawn->GetWorld() != GetWorld() || Pawn->IsActorBeingDestroyed() || IsActorBeingDestroyed()
        || IsHidden() || !GetStaticMeshComponent()->IsVisible() || !Mesh
        || !Mesh->GetPathName().StartsWith(TEXT("/Game/Imported/")) || !Content) return false;
    FWarResourceDefinition Parsed;
    if (!Content->GetResourceNode(ZoneId, NodeId, Parsed, Error)) return false;
    if (Parsed.VisualPropId != VisualPropId) { Error = TEXT("Resource node visual binding is unavailable."); return false; }
    auto Position = Pawn->GetActorLocation();
    if (const auto* Character = Cast<ACharacter>(Pawn)) Position.Z -= Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    const double Distance = Parsed.bMeasureHeight ? FVector::DistSquared(Position, GetActorLocation())
        : FVector::DistSquared2D(Position, GetActorLocation());
    if (!FMath::IsFinite(Distance) || Distance > FMath::Square(Parsed.RadiusCm)) { Error = TEXT("Resource node is too far away."); return false; }
    Definition = MoveTemp(Parsed); Error.Reset(); return true;
}
