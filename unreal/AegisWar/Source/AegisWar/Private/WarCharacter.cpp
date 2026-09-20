#include "WarCharacter.h"
#include "AegisWar.h"
#include "WarAttributeSet.h"
#include "WarCharacterVisualDefinition.h"
#include "WarGameMode.h"
#include "WarPlayerState.h"
#include "WarStrikeAbility.h"
#include "WarTypes.h"
#include "AbilitySystemComponent.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/LocalPlayer.h"
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
    bReplicates = true;
    bUseControllerRotationYaw = false;
    GetCapsuleComponent()->InitCapsuleSize(42.f, 96.f);
    GetCapsuleComponent()->SetHiddenInGame(true);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    GetCharacterMovement()->bOrientRotationToMovement = true;
    GetCharacterMovement()->RotationRate = FRotator(0.f, 540.f, 0.f);
    GetCharacterMovement()->MaxWalkSpeed = 600.f;
    GetCharacterMovement()->JumpZVelocity = 500.f;
    GetCharacterMovement()->AirControl = 0.2f;
    // The inherited capsule is collision only. No visible primitive or default mannequin is installed.
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
    CameraBoom->SetupAttachment(RootComponent);
    CameraBoom->TargetArmLength = 420.f;
    CameraBoom->bUsePawnControlRotation = true;
    FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
    FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
}

void AWarCharacter::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AWarCharacter, VisualDefinition);
    DOREPLIFETIME(AWarCharacter, bDead);
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
    if (!VisualDefinition->AnimationBlueprint.IsNull())
        GetMesh()->SetAnimInstanceClass(VisualDefinition->AnimationBlueprint.LoadSynchronous());
    else GetMesh()->PlayAnimation(VisualDefinition->IdleAnimation.LoadSynchronous(), true);
    bVisualReady = true;
    return true;
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
    if (AWarPlayerState* State = GetPlayerState<AWarPlayerState>()) State->InitializeForPawn(this);
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
    LookYawAction = MakeAction(EInputActionValueType::Axis1D);
    LookPitchAction = MakeAction(EInputActionValueType::Axis1D);
    JumpAction = MakeAction(EInputActionValueType::Boolean);
    StrikeAction = MakeAction(EInputActionValueType::Boolean);
    MappingContext->MapKey(MoveForwardAction, EKeys::W);
    MappingContext->MapKey(MoveForwardAction, EKeys::S).Modifiers.Add(NewObject<UInputModifierNegate>(MappingContext));
    MappingContext->MapKey(MoveRightAction, EKeys::D);
    MappingContext->MapKey(MoveRightAction, EKeys::A).Modifiers.Add(NewObject<UInputModifierNegate>(MappingContext));
    MappingContext->MapKey(LookYawAction, EKeys::MouseX);
    MappingContext->MapKey(LookPitchAction, EKeys::MouseY);
    MappingContext->MapKey(JumpAction, EKeys::SpaceBar);
    MappingContext->MapKey(StrikeAction, EKeys::LeftMouseButton);
    Subsystem->AddMappingContext(MappingContext, 0);
    Input->BindAction(MoveForwardAction, ETriggerEvent::Triggered, this, &AWarCharacter::MoveForward);
    Input->BindAction(MoveRightAction, ETriggerEvent::Triggered, this, &AWarCharacter::MoveRight);
    Input->BindAction(LookYawAction, ETriggerEvent::Triggered, this, &AWarCharacter::LookYaw);
    Input->BindAction(LookPitchAction, ETriggerEvent::Triggered, this, &AWarCharacter::LookPitch);
    Input->BindAction(JumpAction, ETriggerEvent::Started, this, &AWarCharacter::StartJump);
    Input->BindAction(JumpAction, ETriggerEvent::Completed, this, &ACharacter::StopJumping);
    Input->BindAction(StrikeAction, ETriggerEvent::Started, this, &AWarCharacter::RequestStrike);
}

void AWarCharacter::MoveForward(const FInputActionValue& Value)
{
    if (Controller && !bDead && bVisualReady) AddMovementInput(FRotationMatrix(FRotator(0.f, Controller->GetControlRotation().Yaw, 0.f)).GetUnitAxis(EAxis::X), Value.Get<float>());
}
void AWarCharacter::MoveRight(const FInputActionValue& Value)
{
    if (Controller && !bDead && bVisualReady) AddMovementInput(FRotationMatrix(FRotator(0.f, Controller->GetControlRotation().Yaw, 0.f)).GetUnitAxis(EAxis::Y), Value.Get<float>());
}
void AWarCharacter::LookYaw(const FInputActionValue& Value) { AddControllerYawInput(Value.Get<float>()); }
void AWarCharacter::LookPitch(const FInputActionValue& Value) { AddControllerPitchInput(-Value.Get<float>()); }
void AWarCharacter::StartJump() { if (!bDead && bVisualReady) Jump(); }

void AWarCharacter::RequestStrike()
{
    if (bDead || !bVisualReady) return;
    const APlayerController* PC = Cast<APlayerController>(Controller);
    if (!PC) return;
    FVector Origin;
    FRotator Direction;
    PC->GetPlayerViewPoint(Origin, Direction);
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(WarSelectTarget), false, this);
    if (GetWorld()->LineTraceSingleByChannel(Hit, Origin, Origin + Direction.Vector() * 5000.f, ECC_Visibility, Params))
    {
        if (AWarCharacter* Target = Cast<AWarCharacter>(Hit.GetActor())) ServerRequestStrike(Target);
    }
}

void AWarCharacter::ServerRequestStrike_Implementation(AWarCharacter* Target)
{
    const double Now = GetWorld()->GetTimeSeconds();
    if (Now < NextStrikeRequestTime) return;
    NextStrikeRequestTime = Now + 0.1;
    if (!CanStrikeTarget(Target)) return;
    RequestedStrikeTarget = Target;
    GetAbilitySystemComponent()->TryActivateAbilityByClass(UWarStrikeAbility::StaticClass());
    RequestedStrikeTarget.Reset();
}

bool AWarCharacter::CanStrikeTarget(const AWarCharacter* Target) const
{
    if (!HasAuthority() || !IsValid(Target) || Target->GetWorld() != GetWorld()
        || !bVisualReady || !Target->bVisualReady || bDead || Target->bDead) return false;
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
    if (InputSubsystem.IsValid() && MappingContext) InputSubsystem->RemoveMappingContext(MappingContext);
    if (UAbilitySystemComponent* ASC = GetAbilitySystemComponent())
    {
        if (ASC->GetAvatarActor() == this) ASC->ClearActorInfo();
    }
    Super::EndPlay(EndPlayReason);
}
