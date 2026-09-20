#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "AbilitySystemInterface.h"
#include "WarCharacter.generated.h"

class UWarCharacterVisualDefinition;
class USpringArmComponent;
class UCameraComponent;
class UInputAction;
class UInputMappingContext;
class UEnhancedInputLocalPlayerSubsystem;
struct FInputActionValue;

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
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

    bool SetVisualDefinition(UWarCharacterVisualDefinition* Definition, FString& OutError);
    bool IsVisualReady() const { return bVisualReady; }
    bool CanStrikeTarget(const AWarCharacter* Target) const;
    AWarCharacter* GetRequestedStrikeTarget() const { return RequestedStrikeTarget.Get(); }
    void HandleDeath();

protected:
    UPROPERTY(VisibleAnywhere, Category="Camera") TObjectPtr<USpringArmComponent> CameraBoom;
    UPROPERTY(VisibleAnywhere, Category="Camera") TObjectPtr<UCameraComponent> FollowCamera;
    UPROPERTY(ReplicatedUsing=OnRep_VisualDefinition) TObjectPtr<UWarCharacterVisualDefinition> VisualDefinition;
    UPROPERTY(ReplicatedUsing=OnRep_Dead) bool bDead = false;

private:
    UFUNCTION() void OnRep_VisualDefinition();
    UFUNCTION() void OnRep_Dead();
    UFUNCTION(Server, Reliable) void ServerRequestStrike(AWarCharacter* Target);
    bool ApplyVisual(FString& OutError);
    void InitializeAbilityActor();
    void MoveForward(const FInputActionValue& Value);
    void MoveRight(const FInputActionValue& Value);
    void LookYaw(const FInputActionValue& Value);
    void LookPitch(const FInputActionValue& Value);
    void StartJump();
    void RequestStrike();

    UPROPERTY(Transient) TObjectPtr<UInputMappingContext> MappingContext;
    UPROPERTY(Transient) TObjectPtr<UInputAction> MoveForwardAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> MoveRightAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> LookYawAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> LookPitchAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> JumpAction;
    UPROPERTY(Transient) TObjectPtr<UInputAction> StrikeAction;
    TWeakObjectPtr<AWarCharacter> RequestedStrikeTarget;
    TWeakObjectPtr<UEnhancedInputLocalPlayerSubsystem> InputSubsystem;
    double NextStrikeRequestTime = 0.0;
    bool bVisualReady = false;
};
