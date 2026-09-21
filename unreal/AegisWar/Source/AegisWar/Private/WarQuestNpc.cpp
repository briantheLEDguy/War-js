#include "WarQuestNpc.h"
#include "WarCharacterVisualDefinition.h"
#include "WarContentSubsystem.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Character.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimInstance.h"
#include "Net/UnrealNetwork.h"

AWarQuestNpc::AWarQuestNpc()
{
    bReplicates = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Mesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Mesh"));
    Mesh->SetupAttachment(RootComponent);
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void AWarQuestNpc::BeginPlay() { Super::BeginPlay(); OnRep_Visual(); }
void AWarQuestNpc::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AWarQuestNpc, ZoneId);
    DOREPLIFETIME(AWarQuestNpc, NpcId);
    DOREPLIFETIME(AWarQuestNpc, Visual);
}
void AWarQuestNpc::OnRep_Visual()
{
    FString Error;
    if (!Visual || !Visual->ValidateForSpawn(Visual->Realm, Error)) return;
    GetSkeletalMeshComponent()->SetSkeletalMesh(Visual->SkeletalMesh.LoadSynchronous());
    GetSkeletalMeshComponent()->SetRelativeTransform(Visual->MeshTransform);
    if (!Visual->AnimationBlueprint.IsNull())
        Mesh->SetAnimInstanceClass(Visual->AnimationBlueprint.LoadSynchronous());
    else
        Mesh->PlayAnimation(Visual->IdleAnimation.LoadSynchronous(), true);
}
bool AWarQuestNpc::ValidateIdentity(FString& Name, FString& Error, bool* bMeasureHeight) const
{
    Error = TEXT("A required quest NPC model is unavailable.");
    if (IsActorBeingDestroyed() || IsHidden() || !Mesh->IsVisible() || !Mesh->GetSkeletalMeshAsset() || !Visual) return false;
    const auto* Content = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarContentSubsystem>() : nullptr;
    FName Profile; FString ParsedName;
    if (!Content || !Content->GetQuestNpc(ZoneId, NpcId, ParsedName, Profile, Error, bMeasureHeight)
        || !Content->ValidateNpcVisual(Visual, Profile, Error)
        || Mesh->GetSkeletalMeshAsset() != Visual->SkeletalMesh.Get()) return false;
    Name = ParsedName; Error.Reset(); return true;
}
bool AWarQuestNpc::ResolveInteraction(const APawn* Pawn, FString& Name, FString& Error) const
{
    Error = TEXT("Quest NPC is unavailable or too far away.");
    if (!IsValid(Pawn) || Pawn->GetWorld() != GetWorld()) return false;
    bool bHeight = false;
    if (!ValidateIdentity(Name, Error, &bHeight)) return false;
    FVector Position = Pawn->GetActorLocation();
    if (const auto* Character = Cast<ACharacter>(Pawn)) Position.Z -= Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    const double Distance = bHeight ? FVector::DistSquared(Position, GetActorLocation()) : FVector::DistSquared2D(Position, GetActorLocation());
    if (!FMath::IsFinite(Distance) || Distance >= FMath::Square(400.0))
    { Error = TEXT("Move closer to speak to this character."); return false; }
    Error.Reset(); return true;
}
