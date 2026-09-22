#include "WarEnemy.h"
#include "WarCombatStatus.h"
#include "WarNpcEquipment.h"
#include "WarEnemyStateSubsystem.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarContentSubsystem.h"
#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarGameplayEffects.h"
#include "AbilitySystemComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"

AWarEnemy::AWarEnemy()
{
    CombatStatus = CreateDefaultSubobject<UWarCombatStatus>(TEXT("CombatStatus"));
    bReplicates = true; SetReplicateMovement(true); PrimaryActorTick.bCanEverTick = true;
    GetCapsuleComponent()->InitCapsuleSize(42, 96);
    GetCapsuleComponent()->SetHiddenInGame(true);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    TrainingMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("TrainingMesh"));
    TrainingMesh->SetupAttachment(GetRootComponent());
    TrainingMesh->SetCollisionProfileName(TEXT("NoCollision"));
    TrainingMesh->SetRelativeLocation(FVector(0, 0, -96));
    GetCharacterMovement()->bRunPhysicsWithNoController = true;
    GetCharacterMovement()->bOrientRotationToMovement = true;
    GetCharacterMovement()->RotationRate = FRotator(0, 540, 0);
    GetCharacterMovement()->bCanWalkOffLedges = false;
}

void AWarEnemy::PostRegisterAllComponents()
{
    Super::PostRegisterAllComponents();
#if WITH_EDITOR
    if (!IsTemplate() && GetWorld() && !GetWorld()->IsGameWorld() && !bPreparingEditorEquipment
        && Visual && GetMesh()->GetSkeletalMeshAsset())
    {
        TGuardValue<bool> Guard(bPreparingEditorEquipment, true); FString Error;
        UWarNpcEquipmentLibrary::Apply(GetMesh(), Visual->SourceProfileKey, EnemyId, TEXT("enemy"), Error);
    }
#endif
}

void AWarEnemy::BeginPlay()
{
    Super::BeginPlay();
    // A streaming reload can reuse the same actor before GC; retain its authored home.
    if (!bHomeCaptured) { Home = GetActorLocation(); bHomeCaptured = true; }
    FString Error;
    const auto* Content = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarContentSubsystem>() : nullptr;
    bReady = Content && Content->IsContentReady()
        && WarEnemies::Parse(Content->GetInterfaceCatalogSource(), ZoneId, EnemyId, Definition, Error);
    if (bReady)
        bReady = Definition.bTrainingDummy
            ? Content->ValidateWorldVisual(TEXT("training_dummy"), ZoneId, EnemyId, EnemyId, TrainingMesh, Error)
            : Visual && Visual->SourceProfileKey == Definition.Profile
                && Content->ValidateNpcVisual(Visual, Definition.Profile, Error);
    for (TActorIterator<AWarEnemy> It(GetWorld()); It; ++It)
        if (*It != this && It->ZoneId == ZoneId && It->EnemyId == EnemyId) { bReady = false; Error = TEXT("Duplicate enemy identity."); }
    if (bReady && !Definition.bTrainingDummy)
    {
        GetMesh()->SetSkeletalMesh(Visual->SkeletalMesh.LoadSynchronous());
        GetMesh()->SetRelativeTransform(Visual->MeshTransform);
        bReady = UWarNpcEquipmentLibrary::Apply(GetMesh(), Definition.Profile, EnemyId, TEXT("enemy"), Error);
    }
    if (!bReady)
    {
        // Readiness blocks travel; an invalid visual can never become an invisible attacker.
        SetActorHiddenInGame(true); SetActorEnableCollision(false); GetCharacterMovement()->DisableMovement();
        UE_LOG(LogTemp, Error, TEXT("WAR_ENEMY_CONTENT_BLOCKED %s/%s: %s"), *ZoneId.ToString(), *EnemyId.ToString(), *Error);
        if (GetNetMode() == NM_Client)
            if (auto* Local = UGameplayStatics::GetPlayerController(this, 0)) Local->ConsoleCommand(TEXT("disconnect"));
        return;
    }
    CacheInitialMeshOffset(GetMesh()->GetRelativeLocation(), GetMesh()->GetRelativeRotation());
    if (Definition.bTrainingDummy) GetCharacterMovement()->DisableMovement();
    GetCharacterMovement()->MaxWalkSpeed = Definition.MoveSpeed;
    if (HasAuthority())
    {
        auto& Life = GetWorld()->GetSubsystem<UWarEnemyStateSubsystem>()->FindOrCreate(ZoneId, EnemyId, Definition.MaxHealth);
        Health = Life.Health;
    }
    OnRep_Health();
}

void AWarEnemy::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{ Super::GetLifetimeReplicatedProps(OutLifetimeProps); DOREPLIFETIME(AWarEnemy, Health); }

bool AWarEnemy::HasLineOfSight(const AActor* Actor) const
{
    if (!IsValid(Actor)) return false;
    FHitResult Hit; FCollisionQueryParams Params(SCENE_QUERY_STAT(WarEnemySight), false, this);
    return !GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation(), Actor->GetActorLocation(), ECC_Visibility, Params)
        || Hit.GetActor() == Actor;
}

bool AWarEnemy::Eligible(const AWarCharacter* Player, double Range, bool bRequireSight) const
{
    const auto* State = IsValid(Player) ? Player->GetPlayerState<AWarPlayerState>() : nullptr;
    return State && Player->GetWorld() == GetWorld() && State->GetRealm() != EWarRealm::None
        && !Player->IsDevelopmentFlying() && WarEnemies::CanEngage(!Player->IsDead(), Player->IsVisualReady(), ZoneId,
            State->GetCurrentZone(), FVector::DistSquared2D(GetActorLocation(), Player->GetActorLocation()),
            GetActorLocation().Z - Player->GetActorLocation().Z, Range)
        && (!bRequireSight || HasLineOfSight(Player));
}

bool AWarEnemy::CanReceiveStrike(const AWarCharacter* Attacker) const
{
    // Campaign PvE raiders are hostile to both realms, including in their home-side zone.
    return bReady && !IsDead() && !IsHidden() && Eligible(Attacker, WarValidation::StrikeRangeCm, true);
}

bool AWarEnemy::ReceiveStrike(AWarCharacter* Attacker)
{
    const auto* Status = UWarCombatStatus::On(Attacker);
    return ReceiveAbilityDamage(Attacker, WarValidation::StrikeDamage * (Status ? Status->OutgoingScale() : 1), WarValidation::StrikeRangeCm);
}

bool AWarEnemy::CanReceiveAbility(const AWarCharacter* Attacker, float Range, bool bRequireSight) const
{ return bReady && !IsDead() && !IsHidden() && Eligible(Attacker, Range, bRequireSight); }

bool AWarEnemy::ReceiveAbilityDamage(AWarCharacter* Attacker, float Damage, float Range, bool bRequireSight)
{
    if (!HasAuthority() || !FMath::IsFinite(Damage) || Damage <= 0 || !CanReceiveAbility(Attacker, Range, bRequireSight)) return false;
    Damage = CombatStatus->ReceiveDamage(Damage);
    auto& Life = GetWorld()->GetSubsystem<UWarEnemyStateSubsystem>()->FindOrCreate(ZoneId, EnemyId, Definition.MaxHealth);
    const float Remaining = FMath::Max(0.f, Health - Damage);
    if (Remaining == 0)
    {
        if (!Definition.bTrainingDummy)
        {
            TArray<FWarInventoryItem> Loot;
            if (FMath::FRand() <= 0.65f)
            {
                const FName Keys[] = {TEXT("potion_health"), TEXT("potion_health"), TEXT("bread"), TEXT("potion_mana")};
                const auto* Content = GetGameInstance()->GetSubsystem<UWarContentSubsystem>(); FWarInventoryItem Item;
                if (!Content->ResolveInventoryItem(Keys[FMath::RandRange(0, 3)], 1, Item)) return false;
                Loot.Add(Item);
            }
            FString Error;
            if (!Attacker->GetPlayerState<AWarPlayerState>()->AwardEnemyKillTrusted(ZoneId, EnemyId, Life.Event, Loot, Error))
            { UE_LOG(LogTemp, Warning, TEXT("Enemy death reward rejected: %s"), *Error); return false; }
        }
        Life.RespawnAt = GetWorld()->GetTimeSeconds() + WarEnemies::RespawnSeconds;
        Target.Reset(); GetCharacterMovement()->StopMovementImmediately();
    }
    else if (!Definition.bTrainingDummy) Target = Attacker;
    Health = Remaining; Life.Health = Remaining; OnRep_Health(); ForceNetUpdate(); return true;
}

void AWarEnemy::Play(FName Clip, bool bLoop)
{
    if (!bReady || Definition.bTrainingDummy || GetNetMode() == NM_DedicatedServer || PlayingAnimation == Clip) return;
    const auto* Reference = Visual->ImportedAnimations.Find(Clip);
    auto* Animation = Clip == TEXT("idle") ? Visual->IdleAnimation.LoadSynchronous() : Reference ? Reference->LoadSynchronous() : nullptr;
    if (Animation) { GetMesh()->PlayAnimation(Animation, bLoop); PlayingAnimation = Clip; }
}

void AWarEnemy::OnRep_Health()
{
    if (!bReady) return;
    if (Definition.bTrainingDummy)
    {
        TrainingMesh->SetVisibility(!IsDead());
        GetCapsuleComponent()->SetCollisionEnabled(IsDead() ? ECollisionEnabled::NoCollision : ECollisionEnabled::QueryAndPhysics);
        GetCharacterMovement()->DisableMovement();
        return;
    }
    GetCapsuleComponent()->SetCollisionEnabled(IsDead() ? ECollisionEnabled::NoCollision : ECollisionEnabled::QueryAndPhysics);
    if (IsDead()) { GetCharacterMovement()->DisableMovement(); Play(TEXT("death"), false); }
    else if (GetCharacterMovement()->MovementMode == MOVE_None)
    { GetCharacterMovement()->SetMovementMode(MOVE_Walking); PlayingAnimation = NAME_None; }
}

void AWarEnemy::MulticastAttack_Implementation()
{
    if (!bReady || IsDead()) return;
    PlayingAnimation = NAME_None; Play(TEXT("attack_melee"), false);
    const auto* Reference = Visual->ImportedAnimations.Find(TEXT("attack_melee"));
    ActionUntil = GetWorld()->GetTimeSeconds() + (Reference ? Reference->LoadSynchronous()->GetPlayLength() : 0);
}

void AWarEnemy::Attack(AWarCharacter* Player)
{
    if (!HasAuthority() || Definition.bTrainingDummy || CombatStatus->Has(TEXT("stagger")) || CombatStatus->Has(TEXT("silence")) || !Eligible(Player, Definition.AttackRange + 50, true)) return;
    auto* ASC = Player->GetAbilitySystemComponent();
    if (!ASC) return;
    auto Context = ASC->MakeEffectContext(); Context.AddInstigator(this, this);
    auto Spec = ASC->MakeOutgoingSpec(UWarEnemyDamageEffect::StaticClass(), 1, Context);
    if (!Spec.IsValid()) return;
    Spec.Data->SetSetByCallerMagnitude(FName(TEXT("WarEnemyDamage")), -(Definition.AttackDamage + FMath::RandRange(0, 3)) * CombatStatus->OutgoingScale());
    MulticastAttack(); ASC->ApplyGameplayEffectSpecToSelf(*Spec.Data.Get());
    NextAttack = GetWorld()->GetTimeSeconds() + FMath::FRandRange(2, 2.5f);
}

bool AWarEnemy::ResetAtHome(bool bNewLife)
{
    FHitResult Floor; FCollisionQueryParams Params(SCENE_QUERY_STAT(WarEnemyHome), false, this);
    if (!GetWorld()->LineTraceSingleByChannel(Floor, Home + FVector(0, 0, 50), Home - FVector(0, 0, 250), ECC_Visibility, Params)
        || Floor.ImpactNormal.Z < GetCharacterMovement()->GetWalkableFloorZ()) return false;
    const FVector Landing = Floor.ImpactPoint + FVector(0, 0, GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 2);
    if (GetWorld()->OverlapBlockingTestByChannel(Landing, FQuat::Identity, ECC_Pawn,
        FCollisionShape::MakeCapsule(GetCapsuleComponent()->GetScaledCapsuleRadius(), GetCapsuleComponent()->GetScaledCapsuleHalfHeight()), Params)) return false;
    SetActorLocation(Landing, false, nullptr, ETeleportType::TeleportPhysics);
    GetCharacterMovement()->StopMovementImmediately(); Target.Reset(); NextAttack = GetWorld()->GetTimeSeconds() + 1;
    auto& Life = GetWorld()->GetSubsystem<UWarEnemyStateSubsystem>()->FindOrCreate(ZoneId, EnemyId, Definition.MaxHealth);
    if (bNewLife) Life.Event = FGuid::NewGuid();
    Life.RespawnAt = 0; Health = Life.Health = Definition.MaxHealth; ActionUntil = 0;
    CombatStatus->Clear();
    OnRep_Health(); ForceNetUpdate(); return true;
}

void AWarEnemy::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds); if (!bReady || IsHidden() || !GetMesh()->IsVisible()) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (HasAuthority())
    {
        if (IsDead())
        {
            const auto& Life = GetWorld()->GetSubsystem<UWarEnemyStateSubsystem>()->FindOrCreate(ZoneId, EnemyId, Definition.MaxHealth);
            if (Now >= Life.RespawnAt && Now >= NextThink) { NextThink = Now + 0.5; ResetAtHome(true); }
            return;
        }
        if (Definition.bTrainingDummy) return;
        GetCharacterMovement()->MaxWalkSpeed = Definition.MoveSpeed * CombatStatus->MovementScale();
        if (CombatStatus->MovementScale() == 0)
        {
            GetCharacterMovement()->StopMovementImmediately();
            BlockedSince = Now; // A control effect is not a failed path that should reset the encounter.
        }
        if (CombatStatus->Has(TEXT("stagger"))) return;
        if (Now >= NextThink)
        {
            NextThink = Now + 0.2;
            if (FVector::DistSquared2D(GetActorLocation(), Home) > FMath::Square(WarEnemies::LeashRange)
                || Target.IsStale() || (Target.IsValid() && !Eligible(Target.Get(), WarEnemies::LeashRange, false)))
            { ResetAtHome(false); return; }
            if (!Target.IsValid())
            {
                double Closest = FMath::Square(Definition.AggroRange);
                for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
                {
                    auto* Player = Cast<AWarCharacter>(It->Get()->GetPawn());
                    if (!Eligible(Player, Definition.AggroRange, true)) continue;
                    const double Distance = FVector::DistSquared2D(GetActorLocation(), Player->GetActorLocation());
                    if (Distance <= Closest) { Target = Player; Closest = Distance; }
                }
            }
        }
        if (auto* Player = Target.Get())
        {
            if (!Eligible(Player, WarEnemies::LeashRange, false)) { ResetAtHome(false); return; }
            const FVector Delta = Player->GetActorLocation() - GetActorLocation();
            if (Delta.SizeSquared2D() > FMath::Square(Definition.PreferredRange + 75))
            {
                // CharacterMovement sweeps collision and refuses ledges. Navigation/path authoring is a separate gate.
                AddMovementInput(Delta.GetSafeNormal2D());
                if (FVector::DistSquared2D(LastProgressPosition, GetActorLocation()) > 400)
                { LastProgressPosition = GetActorLocation(); BlockedSince = Now; }
                else if (Now - BlockedSince > 3) { ResetAtHome(false); BlockedSince = Now; }
            }
            else { GetCharacterMovement()->StopMovementImmediately(); SetActorRotation(Delta.Rotation()); }
            if (Now >= NextAttack) Attack(Player);
        }
    }
    if (!IsDead() && Now >= ActionUntil) Play(GetVelocity().SizeSquared2D() > 25 ? TEXT("run") : TEXT("idle"), true);
}
