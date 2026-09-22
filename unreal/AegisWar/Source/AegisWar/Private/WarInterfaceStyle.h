#pragma once
#include "Styling/SlateTypes.h"
#include "Brushes/SlateRoundedBoxBrush.h"

namespace WarInterfaceStyle
{
    inline const FLinearColor Background = FLinearColor::FromSRGBColor(FColor(15, 19, 26));
    inline const FLinearColor Sidebar = FLinearColor::FromSRGBColor(FColor(11, 15, 21));
    inline const FLinearColor Surface = FLinearColor::FromSRGBColor(FColor(24, 30, 39));
    inline const FLinearColor Hover = FLinearColor::FromSRGBColor(FColor(40, 44, 49));
    inline const FLinearColor Gold = FLinearColor::FromSRGBColor(FColor(213, 183, 116));
    inline const FLinearColor Line = FLinearColor::FromSRGBColor(FColor(86, 77, 56));
    inline const FLinearColor Text = FLinearColor::FromSRGBColor(FColor(237, 231, 215));
    inline const FLinearColor Muted = FLinearColor::FromSRGBColor(FColor(163, 171, 182));
    inline const FSlateRoundedBoxBrush Frame(Background, 4.f, Line, 1.f);

    // Slate retains brush pointers, so theme resources outlive every widget rebuild.
    inline const FButtonStyle& Button()
    {
        static const FButtonStyle Style = FButtonStyle()
            .SetNormal(FSlateRoundedBoxBrush(Surface, 3.f, Line, 1.f))
            .SetHovered(FSlateRoundedBoxBrush(Hover, 3.f, Gold, 1.f))
            .SetPressed(FSlateRoundedBoxBrush(Sidebar, 3.f, Gold, 1.f))
            .SetNormalForeground(Text).SetHoveredForeground(Gold).SetPressedForeground(Gold)
            .SetNormalPadding(FMargin(0)).SetPressedPadding(FMargin(0));
        return Style;
    }
    inline const FButtonStyle& PrimaryButton()
    {
        static const FButtonStyle Style = FButtonStyle(Button())
            .SetNormal(FSlateRoundedBoxBrush(Gold, 3.f))
            .SetHovered(FSlateRoundedBoxBrush(Text, 3.f))
            .SetPressed(FSlateRoundedBoxBrush(Gold * 0.7f, 3.f))
            .SetNormalForeground(Sidebar).SetHoveredForeground(Sidebar).SetPressedForeground(Sidebar);
        return Style;
    }
}
