#include "WarCharacter.h"
#include "WarAbilityRuntime.h"
#include "WarCombatStatus.h"
#include "WarWrathRelic.h"
#include "AegisWar.h"
#include "WarAttributeSet.h"
#include "WarCharacterVisualDefinition.h"
#include "WarAnimationInstance.h"
#include "WarGameMode.h"
#include "WarSiegeGameMode.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
#include "WarStrikeAbility.h"
#include "WarEnemy.h"
#include "WarTypes.h"
#include "AbilitySystemComponent.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputAction.h"
#include "InputActionValue.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "Kismet/GameplayStatics.h"
#include "Net/UnrealNetwork.h"

AWarCharacter::AWarCharacter()
{
    CombatStatus = CreateDefaultSubobject<UWarCombatStatus>(TEXT("CombatStatus"));
    bReplicates = true;
    PrimaryActorTick.bCanEverTick = true;
    bUseControllerRotationYaw = false;
    GetCapsuleComponent()->InitCapsuleSize(42.f, 96.f);
    GetCapsuleComponent()->SetHiddenInGame(true);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    GetCharacterMovement()->bOrientRotationToMovement = false;
    GetCharacterMovement()->bUseControllerDesiredRotation = true;
    GetCharacterMovement()->RotationRate = FRotator(0.f, 540.f, 0.f);
    GetCharacterMovement()->MaxWalkSpeed = 600.f;
    GetCharacterMovement()->JumpZVelocity = 500.f;
    GetCharacterMovement()->AirControl = 0.2f;
    // The inherited capsule is collision only. No visible primitive or default mannequin is installed.
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Weapon = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("EquippedWeapon"));
    Shield = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("EquippedShield"));
    Weapon->SetupAttachment(GetMesh()); Shield->SetupAttachment(GetMesh());
    Weapon->SetCollisionEnabled(ECollisionEnabled::NoCollision); Shield->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
    CameraBoom->SetupAttachment(RootComponent);
    CameraBoom->TargetArmLength = 700.f;
    CameraBoom->ProbeSize = 35.f;
    CameraBoom->SetRelativeLocation(FVector(0, 0, -6)); // 0.9 m focus above feet, accounting for the 0.96 m capsule half-height.
    CameraBoom->bUsePawnControlRotation = true;
    FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
    FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
}

void AWarCharacter::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AWarCharacter, VisualDefinition);
    DOREPLIFETIME(AWarCharacter, bDead);
    DOREPLIFETIME(AWarCharacter, Motion);
}

UAbilitySystemComponent* AWarCharacter::GetAbilitySystemComponent() const
{
    const AWarPlayerState* State = GetPlayerState<AWarPlayerState>();
    return State ? State->GetAbilitySystemComponent() : nullptr;
}

bool AWarCharacter::SetVisualDefinition(UWarCharacterVisualDefinition* Definition, FString& OutError)
{
    if (!HasAuthority()) { OutError = TEXT("Only the server assigns a character visual."); return false; }
    VisualDefinition = Definition;
    return ApplyVisual(OutError);
}

bool AWarCharacter::ApplyVisual(FString& OutError)
{
    bVisualReady = false;
    const AWarPlayerState* State = GetPlayerState<AWarPlayerState>();
    const EWarRealm ExpectedRealm = State && State->GetRealm() != EWarRealm::None
        ? State->GetRealm() : VisualDefinition ? VisualDefinition->Realm : EWarRealm::None;
    if (!VisualDefinition || !VisualDefinition->ValidateForSpawn(ExpectedRealm, OutError))
    {
        if (OutError.IsEmpty()) OutError = TEXT("Character has no approved imported visual definition.");
        return false;
    }
    GetMesh()->SetSkeletalMesh(VisualDefinition->SkeletalMesh.LoadSynchronous());
    GetMesh()->SetRelativeTransform(VisualDefinition->MeshTransform);
    // Network smoothing restores these cached offsets; update them after the
    // imported mesh transform so remote characters do not float at capsule height.
    CacheInitialMeshOffset(GetMesh()->GetRelativeLocation(), GetMesh()->GetRelativeRotation());
    Weapon->SetStaticMesh(VisualDefinition->WeaponMesh.LoadSynchronous());
    Shield->SetStaticMesh(VisualDefinition->ShieldMesh.LoadSynchronous());
    if (!VisualDefinition->AnimationStyle.IsNone())
        GetMesh()->SetAnimInstanceClass(UWarAnimationInstance::StaticClass());
    else if (!VisualDefinition->AnimationBlueprint.IsNull())
        GetMesh()->SetAnimInstanceClass(VisualDefinition->AnimationBlueprint.LoadSynchronous());
    else
    {
        GetMesh()->PlayAnimation(VisualDefinition->IdleAnimation.LoadSynchronous(), true);
        PlayingAnimation = TEXT("idle");
    }
    bVisualReady = true;
    if (!EquipmentPoseHandle.IsValid())
        EquipmentPoseHandle=GetMesh()->RegisterOnBoneTransformsFinalizedDelegate(
            FOnBoneTransformsFinalizedMultiCast::FDelegate::CreateUObject(this,&AWarCharacter::UpdateEquipmentPresentation));
    if (HasAuthority() && GetPlayerState<AWarPlayerState>()) GetPlayerState<AWarPlayerState>()->GetClassAbilities()->InitializeCharacter(this);
    return true;
}

FName AWarCharacter::GetCareerId() const { return VisualDefinition ? VisualDefinition->ClassId : NAME_None; }
FName AWarCharacter::GetAnimationProfile() const { return VisualDefinition ? VisualDefinition->ProfileKey : NAME_None; }
float AWarCharacter::GetAbilityAnimationDuration(FName MotionRole) const
{
    const auto* Ref = VisualDefinition ? VisualDefinition->ImportedAnimations.Find(MotionRole) : nullptr;
    const auto* Animation = Ref ? Ref->LoadSynchronous() : nullptr;
    return Animation ? Animation->GetPlayLength() : 0;
}
float AWarCharacter::GetBasicAttackContact() const
{ return VisualDefinition ? VisualDefinition->BasicContactSeconds : 0; }
double AWarCharacter::AnimationTime() const
{ const auto* State = GetWorld()->GetGameState(); return State ? State->GetServerWorldTimeSeconds() : GetWorld()->GetTimeSeconds(); }
bool AWarCharacter::IsActionPlaying() const { return AnimationTime() < Motion.Start + Motion.Duration; }
const FWarAbilityPresentation* AWarCharacter::GetAbilityPresentation(FName Ability) const
{ return VisualDefinition ? VisualDefinition->AbilityPresentations.Find(Ability) : nullptr; }
FName AWarCharacter::BeginAbilityPresentation(FName Ability)
{
    const auto* Recipe = GetAbilityPresentation(Ability);
    if (!HasAuthority() || !Recipe || Recipe->VariantRoles.IsEmpty()) return NAME_None;
    int32& NextVariant = PresentationSerials.FindOrAdd(Ability);
    const FName MotionRole = Recipe->VariantRoles[NextVariant % Recipe->VariantRoles.Num()];
    NextVariant = (NextVariant + 1) % Recipe->VariantRoles.Num();
    MulticastPlayAbilityMotion(MotionRole, Recipe->Duration, false);
    Motion.bStowEquipment = Recipe->bStowEquipment;
    return MotionRole;
}
void AWarCharacter::MulticastPlayAbilityMotion_Implementation(FName MotionRole, float Duration, bool bLoop)
{
    if (!HasAuthority() || bDead || !bVisualReady) return;
    Motion.Role = MotionRole; Motion.Start = AnimationTime(); Motion.Duration = FMath::Max(0.f, Duration);
    Motion.bLoop = bLoop; Motion.bStowEquipment = false; ++Motion.Serial; ForceNetUpdate();
    ActionAnimationUntil = GetWorld()->GetTimeSeconds() + Duration;
    if (GetCharacterMovement()->IsMovingOnGround()) GetCharacterMovement()->StopMovementImmediately();
    if (GetNetMode() != NM_DedicatedServer && VisualDefinition->AnimationStyle.IsNone()) { PlayingAnimation = NAME_None; PlayImportedAnimation(MotionRole, bLoop); }
}
void AWarCharacter::ReactToHit(const AActor* Source, float HealthLost)
{
    if (!HasAuthority() || bDead || HealthLost <= 0 || !VisualDefinition || VisualDefinition->AnimationStyle.IsNone()) return;
    const auto* State = GetPlayerState<AWarPlayerState>();
    const bool bSevere = State && State->GetAttributes() && HealthLost >= State->GetAttributes()->GetMaxHealth()*.2f;
    if (IsActionPlaying() && !bSevere) return;
    if (bSevere && State) State->GetClassAbilities()->Interrupt();
    const bool bBack = Source && FVector::DotProduct(GetActorForwardVector(), (Source->GetActorLocation()-GetActorLocation()).GetSafeNormal2D()) < 0;
    const FName MotionRole = bBack ? TEXT("hit_back") : TEXT("hit_front");
    MulticastPlayAbilityMotion(MotionRole, GetAbilityAnimationDuration(MotionRole), false);
}
bool AWarCharacter::CanAbilityTarget(const AActor* Target, float Range, bool bRequireSight) const
{
    if (const auto* Siege = GetWorld()->GetAuthGameMode<AWarSiegeGameMode>(); Siege && (Siege->IsProtected(this) || Siege->IsProtected(Target))) return false;
    if (!bVisualReady || bDead || IsDevelopmentFlying() || !IsValid(Target) || Target == this || Target->GetWorld() != GetWorld() || Target->IsHidden()) return false;
    const auto* Self = GetPlayerState<AWarPlayerState>(); if (!Self || Self->GetRealm() == EWarRealm::None) return false;
    if (const auto* Enemy = Cast<AWarEnemy>(Target)) return Enemy->CanReceiveAbility(this, Range, bRequireSight);
    const auto* OtherPawn = Cast<AWarCharacter>(Target); const auto* Other = OtherPawn ? OtherPawn->GetPlayerState<AWarPlayerState>() : nullptr;
    if (!Other || !OtherPawn->IsVisualReady() || OtherPawn->IsDead() || OtherPawn->IsDevelopmentFlying()
        || Self->GetCurrentZone() != Other->GetCurrentZone() || Other->GetRealm() == EWarRealm::None || Other->GetRealm() == Self->GetRealm()
        || FVector::DistSquared(GetActorLocation(), Target->GetActorLocation()) > FMath::Square(Range)) return false;
    FHitResult Hit; FCollisionQueryParams Params(SCENE_QUERY_STAT(WarAbilitySight), false, this);
    return !bRequireSight || !GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation(), Target->GetActorLocation(), ECC_Visibility, Params) || Hit.GetActor() == Target;
}

void AWarCharacter::PlayImportedAnimation(const FName Name, const bool bLoop)
{
    if (!VisualDefinition || !VisualDefinition->AnimationBlueprint.IsNull() || PlayingAnimation == Name) return;
    const auto* Reference = VisualDefinition->ImportedAnimations.Find(Name);
    UAnimSequence* Animation = Name == TEXT("idle") ? VisualDefinition->IdleAnimation.LoadSynchronous()
        : Reference ? Reference->LoadSynchronous() : nullptr;
    if (!Animation) return; // The visual entry gate rejects incomplete animation sets before spawn.
    GetMesh()->PlayAnimation(Animation, bLoop);
    PlayingAnimation = Name;
}

void AWarCharacter::Tick(const float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bDead && !bDevelopmentFlying)
    {
        const auto* State = GetPlayerState<AWarPlayerState>();
        const bool bBusy = IsActionPlaying() || (State && State->GetClassAbilities()->IsBusy());
        GetCharacterMovement()->MaxWalkSpeed = bBusy ? 0 : (bDevelopmentSpeedsCaptured ? DevelopmentBaseWalkSpeed : 600.f) * DevelopmentSpeed * CombatStatus->MovementScale();
        if ((bBusy || CombatStatus->MovementScale() == 0) && GetCharacterMovement()->IsMovingOnGround()) GetCharacterMovement()->StopMovementImmediately();
    }
    UpdateMovementInput();
    if (!bVisualReady || GetNetMode() == NM_DedicatedServer) return;
    if (!VisualDefinition->AnimationStyle.IsNone()) return; // Selection runs at pose preparation, after movement requests it.
    if (bDead) { PlayImportedAnimation(TEXT("death"), false); return; }
    if (GetWorld()->GetTimeSeconds() < ActionAnimationUntil) return;
    const float Speed = GetVelocity().Size2D();
    PlayImportedAnimation(GetCharacterMovement()->IsFalling() ? TEXT("jump")
        : Speed > 300.f ? TEXT("run") : Speed > 5.f ? TEXT("walk") : TEXT("idle"), true);
}

void AWarCharacter::UpdateNativeAnimation(float Delta)
{
    auto* Instance = Cast<UWarAnimationInstance>(GetMesh()->GetAnimInstance());
    if (!Instance) return;
    const double Now = AnimationTime();
    const bool bFalling = GetCharacterMovement()->IsFalling();
    if (bWasFalling && !bFalling && !IsActionPlaying()) LandingUntil = Now + GetAbilityAnimationDuration(TEXT("landing"));
    bWasFalling = bFalling;
    const FVector Local = GetActorQuat().UnrotateVector(GetVelocity());
    const float Yaw = GetActorRotation().Yaw, YawDelta = FMath::FindDeltaAngleDegrees(PreviousYaw, Yaw);
    PreviousYaw = Yaw;
    FName MotionRole = TEXT("idle"); bool bLoop = true;
    if (bDead) { MotionRole = TEXT("death"); bLoop = false; }
    else if (IsActionPlaying()) { MotionRole = Motion.Role; bLoop = Motion.bLoop; }
    else if (bFalling) { MotionRole = TEXT("jump"); bLoop = false; }
    else if (Now < LandingUntil) { MotionRole = TEXT("landing"); bLoop = false; }
    else if (Local.SizeSquared2D() > 25)
    {
        if (FMath::Abs(Local.Y) > FMath::Abs(Local.X)*.8f) MotionRole = Local.Y < 0 ? TEXT("strafe_left") : TEXT("strafe_right");
        else if (Local.X < -5) MotionRole = TEXT("walk_backward");
        else MotionRole = Local.Size2D() > 300 ? TEXT("run") : TEXT("walk");
    }
    else
    {
        if (FMath::Abs(YawDelta) > FMath::Max(.4f, Delta*20) && Now >= TurnUntil)
        { TurnRole = YawDelta < 0 ? TEXT("turn_left") : TEXT("turn_right"); TurnUntil = Now + GetAbilityAnimationDuration(TurnRole); }
        if (Now < TurnUntil) { MotionRole = TurnRole; bLoop = false; }
    }
    if (LocomotionRole != MotionRole) { LocomotionRole = MotionRole; LocomotionStart = Now; LocomotionPhase = 0; }
    const auto* Reference = VisualDefinition->ImportedAnimations.Find(MotionRole);
    UAnimSequence* Clip = Reference ? Reference->LoadSynchronous() : nullptr;
    if (!Clip) return;
    const bool bAction = !bDead && IsActionPlaying();
    float Elapsed = FMath::Max(0., Now-((bAction || bDead) ? Motion.Start : LocomotionStart));
    if (!bAction && bLoop)
    {
        const float ReferenceSpeed = VisualDefinition->LocomotionSpeeds.FindRef(MotionRole);
        if (ReferenceSpeed > 1)
        { LocomotionPhase += Delta * Local.Size2D()/ReferenceSpeed; Elapsed = LocomotionPhase; }
    }
    if (bLoop) Elapsed = FMath::Fmod(Elapsed, FMath::Max(.001f, Clip->GetPlayLength()));
    const FName State = bAction ? FName(*(MotionRole.ToString()+FString::Printf(TEXT(":%d"), Motion.Serial))) : MotionRole;
    Instance->Select(Clip, State, Elapsed); PlayingAnimation = MotionRole;
}

void AWarCharacter::UpdateEquipmentPresentation()
{
    if (!bVisualReady || !VisualDefinition) return;
    // Follow this frame's finalized bones, avoiding a frame of visible grip lag
    // during fast strikes and while the network corrects the mesh transform.
    const bool bAction=!bDead && IsActionPlaying();
    float Elapsed=FMath::Max(0.,AnimationTime()-Motion.Start);
    if (bDead) { UpdateReleasedEquipment(Elapsed); return; }
    // Parallel pose evaluation can finish one tick after action selection.
    // Attachment handoffs must follow the pose currently on screen.
    if (bAction) if (const auto* Animation=Cast<UWarAnimationInstance>(GetMesh()->GetAnimInstance()))
        if (Animation->EvaluatedState==FName(*(Motion.Role.ToString()+FString::Printf(TEXT(":%d"),Motion.Serial))))
            Elapsed=Animation->EvaluatedTime;
    float Stow = bAction && Motion.bStowEquipment ? FMath::Clamp(FMath::Min(Elapsed/.3f, (Motion.Duration-Elapsed)/.3f), 0.f, 1.f) : 0;
    if (VisualDefinition->AnimationStyle == TEXT("spell")) Stow = 1;
    const auto PositionEquipment = [&](UStaticMeshComponent* Part, const FName Hand, const FTransform& Grip, const FTransform& Stored)
    {
        if (!Part->GetStaticMesh()) return;
        // Supplied transition poses carry the grip to/from the back. Equipment
        // remains in the hand until it reaches its stored attachment.
        const bool bStored=Stow>=1-KINDA_SMALL_NUMBER;
        const FName Socket=bStored ? FName(TEXT("upper_chest")) : Hand;
        if (Part->GetAttachParent()!=GetMesh() || Part->GetAttachSocketName()!=Socket)
            Part->AttachToComponent(GetMesh(),FAttachmentTransformRules::KeepRelativeTransform,Socket);
        Part->SetRelativeTransform(bStored ? Stored : Grip);
    };
    PositionEquipment(Weapon, TEXT("hand_R"), VisualDefinition->WeaponGrip, VisualDefinition->WeaponStowed);
    PositionEquipment(Shield, TEXT("hand_L"), VisualDefinition->ShieldGrip, VisualDefinition->ShieldStowed);
}

void AWarCharacter::UpdateReleasedEquipment(float Elapsed)
{
    // Released props settle beside the corpse instead of following a hand
    // through the floor. They remain cosmetic and cannot create combat hits.
    UStaticMeshComponent* Parts[2]={Weapon,Shield};
    if (!bEquipmentReleased)
    {
        for (int32 Index=0;Index<2;++Index)
        {
            auto* Part=Parts[Index]; if (!Part->GetStaticMesh()) continue;
            Part->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
            ReleasedStart[Index]=Part->GetComponentTransform();
            FTransform End(FRotator(90,GetActorRotation().Yaw,0));
            const FBox Bounds=Part->GetStaticMesh()->GetBoundingBox().TransformBy(End);
            FVector Center=GetActorLocation()+GetActorRightVector()*(Index==0?65.f:-65.f);
            FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(WarDroppedEquipment),false,this);
            if (GetWorld()->LineTraceSingleByChannel(Hit,Center+FVector(0,0,100),Center-FVector(0,0,500),ECC_Visibility,Query)) Center.Z=Hit.ImpactPoint.Z;
            else Center.Z=GetActorLocation().Z-GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
            Center.Z+=1-Bounds.Min.Z;
            Center.X-=Bounds.GetCenter().X; Center.Y-=Bounds.GetCenter().Y;
            End.SetLocation(Center); ReleasedEnd[Index]=End;
        }
        bEquipmentReleased=true;
    }
    const float Phase=FMath::Clamp(Elapsed/.8f,0.f,1.f);
    for (int32 Index=0;Index<2;++Index)
    {
        auto* Part=Parts[Index]; if (!Part->GetStaticMesh()) continue;
        FTransform Pose; Pose.Blend(ReleasedStart[Index],ReleasedEnd[Index],Phase*Phase*(3-2*Phase));
        const FBox Local=Part->GetStaticMesh()->GetBoundingBox();
        const float Floor=Local.TransformBy(ReleasedEnd[Index]).Min.Z;
        Pose.AddToTranslation(FVector(0,0,FMath::Max(0.,Floor-Local.TransformBy(Pose).Min.Z)));
        Part->SetWorldTransform(Pose);
    }
}

void AWarCharacter::OnRep_VisualDefinition()
{
    FString Error;
    if (ApplyVisual(Error)) return;
    UE_LOG(LogAegisWar, Error, TEXT("Client cannot display required character content: %s"), *Error);
    // A content mismatch must disconnect the viewer, never permit combat against an invisible actor.
    if (APlayerController* Local = UGameplayStatics::GetPlayerController(this, 0))
    {
        Local->SetIgnoreMoveInput(true);
        Local->SetIgnoreLookInput(true);
        Local->ConsoleCommand(TEXT("disconnect"));
    }
}

void AWarCharacter::InitializeAbilityActor()
{
    if (AWarPlayerState* State = GetPlayerState<AWarPlayerState>())
    { State->InitializeForPawn(this); if (bVisualReady) State->GetClassAbilities()->InitializeCharacter(this); }
}

void AWarCharacter::PossessedBy(AController* NewController)
{
    Super::PossessedBy(NewController);
    InitializeAbilityActor();
}

void AWarCharacter::OnRep_PlayerState()
{
    Super::OnRep_PlayerState();
    InitializeAbilityActor();
    if (VisualDefinition) OnRep_VisualDefinition();
}

void AWarCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
    Super::SetupPlayerInputComponent(PlayerInputComponent);
    UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(PlayerInputComponent);
    const APlayerController* PC = Cast<APlayerController>(Controller);
    if (!Input || !PC || !PC->GetLocalPlayer()) return;
    UEnhancedInputLocalPlayerSubsystem* Subsystem = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer());
    if (!Subsystem) return;
    InputSubsystem = Subsystem;
    if (MappingContext) Subsystem->RemoveMappingContext(MappingContext);
    MappingContext = NewObject<UInputMappingContext>(this);
    const auto MakeAction = [this](const EInputActionValueType Type) {
        UInputAction* Action = NewObject<UInputAction>(this);
        Action->ValueType = Type;
        return Action;
    };
    MoveForwardAction = MakeAction(EInputActionValueType::Axis1D);
    MoveRightAction = MakeAction(EInputActionValueType::Axis1D);
    MoveForwardAction->AccumulationBehavior = EInputActionAccumulationBehavior::Cumulative;
    MoveRightAction->AccumulationBehavior = EInputActionAccumulationBehavior::Cumulative;
    LookYawAction = MakeAction(EInputActionValueType::Axis1D);
    LookPitchAction = MakeAction(EInputActionValueType::Axis1D);
    ZoomAction = MakeAction(EInputActionValueType::Axis1D);
    JumpAction = MakeAction(EInputActionValueType::Boolean);
    StrikeAction = MakeAction(EInputActionValueType::Boolean);
    AutoRunAction = MakeAction(EInputActionValueType::Boolean);
    RefreshControlMappings();
    Subsystem->AddMappingContext(MappingContext, 0);
    Input->BindAction(MoveForwardAction, ETriggerEvent::Triggered, this, &AWarCharacter::MoveForward);
    Input->BindAction(MoveRightAction, ETriggerEvent::Triggered, this, &AWarCharacter::MoveRight);
    for (const auto Event : {ETriggerEvent::Completed, ETriggerEvent::Canceled})
    {
        Input->BindAction(MoveForwardAction, Event, this, &AWarCharacter::MoveForward);
        Input->BindAction(MoveRightAction, Event, this, &AWarCharacter::MoveRight);
    }
    Input->BindAction(LookYawAction, ETriggerEvent::Triggered, this, &AWarCharacter::LookYaw);
    Input->BindAction(LookPitchAction, ETriggerEvent::Triggered, this, &AWarCharacter::LookPitch);
    Input->BindAction(ZoomAction, ETriggerEvent::Triggered, this, &AWarCharacter::Zoom);
    Input->BindAction(JumpAction, ETriggerEvent::Started, this, &AWarCharacter::StartJump);
    Input->BindAction(JumpAction, ETriggerEvent::Completed, this, &ACharacter::StopJumping);
    Input->BindAction(StrikeAction, ETriggerEvent::Started, this, &AWarCharacter::RequestStrike);
    Input->BindAction(AutoRunAction, ETriggerEvent::Started, this, &AWarCharacter::ToggleAutoRun);
    if (auto* Player = Cast<AWarPlayerController>(Controller)) Player->InitializeCameraYaw(Controller->GetControlRotation().Yaw);
    UpdateCamera();
}

void AWarCharacter::RefreshControlMappings()
{
    const auto* PC = Cast<AWarPlayerController>(Controller);
    if (!PC || !MappingContext || !InputSubsystem.IsValid()) return;
    ForwardAxis=0; RightAxis=0;
    MappingContext->UnmapAll();
    MappingContext->MapKey(MoveForwardAction, PC->GetControlKey(TEXT("Forward")));
    MappingContext->MapKey(MoveForwardAction, PC->GetControlKey(TEXT("Backward"))).Modifiers.Add(NewObject<UInputModifierNegate>(MappingContext));
    MappingContext->MapKey(MoveRightAction, PC->GetControlKey(TEXT("Right")));
    MappingContext->MapKey(MoveRightAction, PC->GetControlKey(TEXT("Left"))).Modifiers.Add(NewObject<UInputModifierNegate>(MappingContext));
    MappingContext->MapKey(LookYawAction, EKeys::MouseX);
    MappingContext->MapKey(LookPitchAction, EKeys::MouseY);
    MappingContext->MapKey(ZoomAction, EKeys::MouseWheelAxis);
    MappingContext->MapKey(JumpAction, PC->GetControlKey(TEXT("Jump")));
    MappingContext->MapKey(StrikeAction, PC->GetControlKey(TEXT("Strike")));
    MappingContext->MapKey(AutoRunAction, PC->GetControlKey(TEXT("AutoRun")));
    InputSubsystem->RequestRebuildControlMappings();
}

void AWarCharacter::MoveForward(const FInputActionValue& Value)
{
    ForwardAxis = Value.Get<float>();
}
void AWarCharacter::MoveRight(const FInputActionValue& Value)
{
    RightAxis = Value.Get<float>();
}
void AWarCharacter::ToggleAutoRun()
{
    MovementInput.Toggle(IsLocallyControlled() && Controller && !Controller->IsMoveInputIgnored() && !bDead && bVisualReady
        && GetCharacterMovement()->MovementMode != MOVE_Flying);
}
void AWarCharacter::UpdateMovementInput()
{
    if (bDead) MovementInput.bAutoRun = false;
    const auto* PC = Cast<AWarPlayerController>(Controller);
    if (!IsLocallyControlled() || !PC) return;
    const bool bAllowed = !PC->IsMoveInputIgnored() && !bDead && bVisualReady && !IsActionPlaying() && CombatStatus->MovementScale() > 0;
    const bool bManualKey = PC->IsInputKeyDown(PC->GetControlKey(TEXT("Forward"))) || PC->IsInputKeyDown(PC->GetControlKey(TEXT("Backward")))
        || PC->IsInputKeyDown(PC->GetControlKey(TEXT("Left"))) || PC->IsInputKeyDown(PC->GetControlKey(TEXT("Right")))
        || !FMath::IsNearlyZero(ForwardAxis) || !FMath::IsNearlyZero(RightAxis);
    const auto Intent = MovementInput.Resolve(ForwardAxis, RightAxis, bManualKey,
        PC->IsInputKeyDown(PC->GetControlKey(TEXT("Strike"))) && PC->IsInputKeyDown(PC->GetControlKey(TEXT("Orbit"))),
        bAllowed, bDead || GetCharacterMovement()->MovementMode == MOVE_Flying);
    if (!bAllowed) { ForwardAxis = 0; RightAxis = 0; return; }
    const FRotationMatrix Basis(FRotator(0.f, PC->GetControlRotation().Yaw, 0.f));
    AddMovementInput(Basis.GetUnitAxis(EAxis::X), Intent.X);
    AddMovementInput(Basis.GetUnitAxis(EAxis::Y), Intent.Y);
    if (IsDevelopmentFlying())
        AddMovementInput(FVector::UpVector, (PC->IsInputKeyDown(PC->GetControlKey(TEXT("Interact"))) ? 1.f : 0.f) - (PC->IsInputKeyDown(PC->GetControlKey(TEXT("FlyDown"))) ? 1.f : 0.f));
}
void AWarCharacter::LookYaw(const FInputActionValue& Value)
{
    const auto* PC = Cast<AWarPlayerController>(Controller);
    if (PC && (PC->IsInputKeyDown(PC->GetControlKey(TEXT("Strike"))) || PC->IsInputKeyDown(PC->GetControlKey(TEXT("Orbit")))))
        ApplyCameraOrbit(Value.Get<float>(), 0.0);
}
void AWarCharacter::LookPitch(const FInputActionValue& Value)
{
    const auto* PC = Cast<AWarPlayerController>(Controller);
    if (PC && (PC->IsInputKeyDown(PC->GetControlKey(TEXT("Strike"))) || PC->IsInputKeyDown(PC->GetControlKey(TEXT("Orbit")))))
        ApplyCameraOrbit(0.0, -Value.Get<float>());
}
void AWarCharacter::Zoom(const FInputActionValue& Value)
{
    // Unreal reports wheel notches; use the browser's conventional 100-pixel wheel step.
    ApplyCameraWheel(-Value.Get<float>() * 100.0);
}
bool AWarCharacter::CanControlCamera() const
{
    if (const auto* PC = Cast<AWarPlayerController>(Controller); PC && PC->IsEditingUi()) return false;
    return IsLocallyControlled() && GetCameraState() && !Controller->IsLookInputIgnored() && bVisualReady && !bDead;
}
FWarCameraState* AWarCharacter::GetCameraState() const
{
    auto* Player = Cast<AWarPlayerController>(Controller);
    return Player ? &Player->GetLocalCameraState() : nullptr;
}
double AWarCharacter::GetCameraDistance() const
{
    const auto* State = GetCameraState();
    return State ? State->Distance : CameraBoom->TargetArmLength;
}
void AWarCharacter::UpdateCamera()
{
    const auto* State = GetCameraState();
    if (!State || !IsLocallyControlled()) return;
    CameraBoom->TargetArmLength = State->Distance;
    Controller->SetControlRotation(FRotator(State->Pitch, State->Yaw, 0));
}
void AWarCharacter::ApplyCameraOrbit(double X, double Y)
{
    if (!CanControlCamera()) return;
    GetCameraState()->OrbitPixels(X, Y); UpdateCamera();
}
void AWarCharacter::ApplyCameraWheel(double DeltaPixels)
{
    if (!CanControlCamera()) return;
    GetCameraState()->WheelPixels(DeltaPixels); UpdateCamera();
}
void AWarCharacter::SetCameraIndoorMode(bool bEnabled)
{
    if (!IsLocallyControlled() || !GetCameraState()) return;
    GetCameraState()->SetIndoor(bEnabled); UpdateCamera();
}
void AWarCharacter::SetCameraPreferences(float LookSensitivity, float ZoomSensitivity, bool bInvertX, bool bInvertY)
{
    if (IsLocallyControlled() && GetCameraState()) GetCameraState()->SetPreferences(LookSensitivity, ZoomSensitivity, bInvertX, bInvertY);
}
void AWarCharacter::StartJump() { if (Controller && !Controller->IsMoveInputIgnored() && !bDead && bVisualReady && !IsActionPlaying() && CombatStatus->MovementScale() > 0) Jump(); }

void AWarCharacter::RequestStrike()
{
    if (bDead || !bVisualReady) return;
    const APlayerController* PC = Cast<APlayerController>(Controller);
    if (!PC || PC->IsMoveInputIgnored()) return;
    if (PC->bShowMouseCursor) return;
    FVector Origin;
    FRotator Direction;
    PC->GetPlayerViewPoint(Origin, Direction);
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(WarSelectTarget), false, this);
    if (GetWorld()->LineTraceSingleByChannel(Hit, Origin, Origin + Direction.Vector() * 5000.f, ECC_Visibility, Params))
    {
        RequestTargetStrike(Hit.GetActor());
    }
}

void AWarCharacter::RequestTargetStrike(AActor* Target)
{
    if (IsLocallyControlled() && Controller && !Controller->IsMoveInputIgnored()
        && !bDead && bVisualReady && IsValid(Target)) ServerRequestStrike(Target);
}

void AWarCharacter::ServerRequestStrike_Implementation(AActor* Target)
{
    const double Now = GetWorld()->GetTimeSeconds();
    if (Now < NextStrikeRequestTime) return;
    NextStrikeRequestTime = Now + 0.1;
    if (!CanStrikeTarget(Target)) return;
    const auto* State = GetPlayerState<AWarPlayerState>();
    if (IsActionPlaying() || CombatStatus->Has(TEXT("stagger")) || (State && State->GetClassAbilities()->IsBusy())) return;
    RequestedStrikeTarget = Target;
    GetAbilitySystemComponent()->TryActivateAbilityByClass(UWarStrikeAbility::StaticClass());
    RequestedStrikeTarget.Reset();
}

bool AWarCharacter::CanStrikeTarget(const AActor* Actor) const
{
    if (const auto* Siege = GetWorld()->GetAuthGameMode<AWarSiegeGameMode>(); Siege && (Siege->IsProtected(this) || Siege->IsProtected(Actor))) return false;
    if (!HasAuthority() || !bVisualReady || bDead || !GetAbilitySystemComponent() || GetCharacterMovement()->IsFalling()) return false;
    if (const auto* Enemy = Cast<AWarEnemy>(Actor)) return Enemy->CanReceiveStrike(this);
    const auto* Target = Cast<AWarCharacter>(Actor);
    if (!IsValid(Target) || Target->GetWorld() != GetWorld() || !Target->bVisualReady || Target->bDead) return false;
    const AWarPlayerState* SelfState = GetPlayerState<AWarPlayerState>();
    const AWarPlayerState* TargetState = Target->GetPlayerState<AWarPlayerState>();
    if (!SelfState || !TargetState || !GetAbilitySystemComponent() || !Target->GetAbilitySystemComponent()) return false;
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(WarStrikeVisibility), false, this);
    const bool bBlocked = GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation(), Target->GetActorLocation(), ECC_Visibility, Params);
    return WarValidation::CanStrike(SelfState->GetRealm(), TargetState->GetRealm(),
        SelfState->GetAttributes()->GetHealth(), TargetState->GetAttributes()->GetHealth(),
        FVector::DistSquared(GetActorLocation(), Target->GetActorLocation()), !bBlocked || Hit.GetActor() == Target, this == Target);
}

void AWarCharacter::HandleDeath()
{
    if (!HasAuthority() || bDead) return;
    bDead = true;
    Motion.Role=TEXT("death"); Motion.Start=AnimationTime(); Motion.Duration=GetAbilityAnimationDuration(TEXT("death"));
    Motion.bLoop=false; Motion.bStowEquipment=false; ++Motion.Serial; ForceNetUpdate();
    AWarWrathRelic::RemoveFor(this);
    OnRep_Dead();
    if (AWarGameMode* Mode = GetWorld()->GetAuthGameMode<AWarGameMode>()) Mode->RespawnAfterDeath(this);
}

void AWarCharacter::OnRep_Dead()
{
    if (!bDead) return;
    GetCharacterMovement()->DisableMovement();
    GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void AWarCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    if (EquipmentPoseHandle.IsValid()) GetMesh()->UnregisterOnBoneTransformsFinalizedDelegate(EquipmentPoseHandle);
    EquipmentPoseHandle.Reset();
    AWarWrathRelic::RemoveFor(this);
    if (InputSubsystem.IsValid() && MappingContext) InputSubsystem->RemoveMappingContext(MappingContext);
    if (UAbilitySystemComponent* ASC = GetAbilitySystemComponent())
    {
        if (ASC->GetAvatarActor() == this) ASC->ClearActorInfo();
    }
    Super::EndPlay(EndPlayReason);
}
