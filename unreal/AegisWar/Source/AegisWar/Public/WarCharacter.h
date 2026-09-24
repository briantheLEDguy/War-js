#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "AbilitySystemInterface.h"
#include "WarCameraRules.h"
#include "WarMovementInput.h"
#include "WarCharacter.generated.h"

class UWarCharacterVisualDefinition;
class USpringArmComponent;
class UCameraComponent;
class UInputAction;
class UInputMappingContext;
class UEnhancedInputLocalPlayerSubsystem;
struct FInputActionValue;
struct FWarAbilityPresentation;

USTRUCT()
struct FWarReplicatedMotion
{
    GENERATED_BODY()
    UPROPERTY() FName Role;
    UPROPERTY() double Start = 0;
    UPROPERTY() float Duration = 0;
    UPROPERTY() bool bLoop = false;
    UPROPERTY() bool bStowEquipment = false;
    UPROPERTY() int32 Serial = 0;
};

UCLASS()
class AEGISWAR_API AWarCharacter : public ACharacter, public IAbilitySystemInterface
{
    GENERATED_BODY()
public:
    AWarCharacter();
    virtual UAbilitySystemComponent* GetAbilitySystemComponent() const override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void PossessedBy(AController* NewController) override;
    virtual void OnRep_PlayerState() override;
    virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
    void RefreshControlMappings();
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void Tick(float DeltaSeconds) override;

    bool SetVisualDefinition(UWarCharacterVisualDefinition* Definition, FString& OutError);
    bool IsDead() const { return bDead; }
    bool IsVisualReady() const { return bVisualReady; }
    FName GetCareerId() const;
    FName GetAnimationProfile() const;
    bool CanAbilityTarget(const AActor* Target, float Range, bool bRequireSight = true) const;
    float GetAbilityAnimationDuration(FName MotionRole) const;
    float GetBasicAttackContact() const;
    const FWarAbilityPresentation* GetAbilityPresentation(FName Ability) const;
    FName BeginAbilityPresentation(FName Ability);
    void ReactToHit(const AActor* Source, float HealthLost);
    const FWarReplicatedMotion& GetReplicatedMotion() const { return Motion; }
    bool IsActionPlaying() const;
    UFUNCTION(NetMulticast, Reliable) void MulticastPlayAbilityMotion(FName MotionRole, float Duration, bool bLoop);
    FName GetPlayingAnimation() const { return PlayingAnimation; }
    bool CanStrikeTarget(const AActor* Target) const;
    AActor* GetRequestedStrikeTarget() const { return RequestedStrikeTarget.Get(); }
    void HandleDeath();
    /** The server revalidates target, range, realm, cost and cooldown for every request. */
    UFUNCTION(BlueprintCallable, Category="Combat") void RequestTargetStrike(AActor* Target);
    void ApplyCameraOrbit(double X, double Y);
    void ApplyCameraWheel(double DeltaPixels);
    UFUNCTION(BlueprintCallable, Category="Camera") void SetCameraIndoorMode(bool bEnabled);
    UFUNCTION(BlueprintCallable, Category="Camera") void SetCameraPreferences(float LookSensitivity, float ZoomSensitivity, bool bInvertX, bool bInvertY);
    double GetCameraDistance() const;
    UFUNCTION(BlueprintCallable, Category="Movement") void ToggleAutoRun();
    bool IsAutoRunning() const { return MovementInput.bAutoRun; }
    bool SetDevelopmentTraversal(bool bFlying, float SpeedMultiplier, FString& Error);
    bool ReturnToDevelopmentSpawn(FString& Error);
    bool IsDevelopmentFlying() const { return bDevelopmentFlying && !bDead; }
    float GetDevelopmentSpeed() const { return DevelopmentSpeed; }

protected:
    UPROPERTY(VisibleAnywhere, Category="Camera") TObjectPtr<USpringArmComponent> CameraBoom;
    UPROPERTY(VisibleAnywhere, Category="Camera") TObjectPtr<UCameraComponent> FollowCamera;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UWarCombatStatus> CombatStatus;
    UPROPERTY(ReplicatedUsing=OnRep_VisualDefinition) TObjectPtr<UWarCharacterVisualDefinition> VisualDefinition;
    UPROPERTY(ReplicatedUsing=OnRep_Dead) bool bDead = false;
    UPROPERTY(Replicated) FWarReplicatedMotion Motion;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UStaticMeshComponent> Weapon;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UStaticMeshComponent> Shield;

private:
    friend class UWarAnimationInstance;
    UFUNCTION() void OnRep_VisualDefinition();
    UFUNCTION() void OnRep_Dead();
    UFUNCTION(Server, Reliable) void ServerRequestStrike(AActor* Target);
    bool ApplyVisual(FString& OutError);
    void PlayImportedAnimation(FName Name, bool bLoop);
    void UpdateNativeAnimation(float Delta);
    void UpdateEquipmentPresentation();
    void UpdateReleasedEquipment(float Elapsed);
    double AnimationTime() const;
    void InitializeAbilityActor();
    void MoveForward(const FInputActionValue& Value);
    void MoveRight(const FInputActionValue& Value);
    void LookYaw(const FInputActionValue& Value);
    void LookPitch(const FInputActionValue& Value);
    void Zoom(const FInputActionValue& Value);
    void UpdateCamera();
    bool CanControlCamera() const;
    FWarCameraState* GetCameraState() const;
    void StartJump();
    void UpdateMovementInput();
    void RequestStrike();

    UPROPERTY(Transient) TObjectPtr<UInputMappingContext> MappingContext;
    UPROPERTY(Transient) TObjectPtr<UInputAction> MoveForwardAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> MoveRightAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> LookYawAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> LookPitchAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> ZoomAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> JumpAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> StrikeAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> AutoRunAction;
    FWarMovementInput MovementInput;
    double ForwardAxis = 0.0, RightAxis = 0.0;
    TWeakObjectPtr<AActor> RequestedStrikeTarget;
    TWeakObjectPtr<UEnhancedInputLocalPlayerSubsystem> InputSubsystem;
    double NextStrikeRequestTime = 0.0;
    bool bVisualReady = false;
    FName PlayingAnimation;
    double ActionAnimationUntil = 0.0;
    double LocomotionStart = 0, TurnUntil = 0, LandingUntil = 0;
    bool bWasFalling = false;
    float PreviousYaw = 0;
    float LocomotionPhase = 0;
    FName LocomotionRole, TurnRole;
    TMap<FName, int32> PresentationSerials;
    bool bEquipmentReleased = false;
    FDelegateHandle EquipmentPoseHandle;
    FTransform ReleasedStart[2], ReleasedEnd[2];
    bool bDevelopmentFlying = false, bDevelopmentSpeedsCaptured = false;
    float DevelopmentSpeed = 1.f, DevelopmentBaseWalkSpeed = 600.f, DevelopmentBaseFlySpeed = 600.f;
    float DevelopmentBaseBraking = 0.f;
    ECollisionEnabled::Type DevelopmentCollision = ECollisionEnabled::QueryAndPhysics;
};
